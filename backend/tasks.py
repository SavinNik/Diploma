import logging
import requests
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from backend.models import ProductInfo, Shop, Category, Parameter, ProductParameter, Product, User
import yaml
from yaml import load as load_yaml, Loader
from backend.utils import validate_url

logger = logging.getLogger(__name__)


@shared_task
def send_email(subject, message, from_email, recipient_list):
    """
    Отправка электронной почты с уведомлением о заказе

    Args:
        subject: Тема письма
        message: Сообщение письма
        from_email: Адрес отправителя
        recipient_list: Список получателей
    """
    msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
    msg.send()


@shared_task(bind=True, max_retries=3)
def do_import(self, url, user_id=None):
    """
    Импорт данных из YAML-файла

    Args:
        self: Экземпляр задачи Celery
        url: URL-адрес YAML-файла
        user_id: id авторизированного пользователя
    """
    try:
        if not url:
            raise ValueError("URL не указан")

        # Валидация URL
        if not validate_url(url):
            raise ValidationError("Неверный URL")

        # Получение данных
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        stream = response.content
        data = yaml.safe_load(stream)

        # Проверка наличия необходимых данных
        required_fields = ['shop', 'categories', 'goods']
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Отсутствует обязательное поле: {field}")

        # Получаем пользователя
        if user_id is None:
            raise ValueError('Пользователь не указан')
        try:
            user = User.objects.get(id=user_id, user_type='shop')
        except ObjectDoesNotExist:
            raise ValueError("Пользователь не найден")

        # Создаем магазин
        shop, _ = Shop.objects.get_or_create(
            name=data['shop'],
            user=user
        )

        # Обработка категорий
        for category in data['categories']:
            category_obj, created = Category.objects.get_or_create(
                id=category['id'],
                defaults={'name': category['name']}
            )
            if not created:
                category_obj.name = category['name']
                category_obj.save()
            category_obj.shops.add(shop)

        # Импорт товаров в транзакции
        with transaction.atomic():
            # Очистка старых данных
            ProductInfo.objects.filter(shop=shop).delete()

            for item in data['goods']:
                # Проверка обязательных полей товара
                required_item_fields = ['id', 'category', 'model', 'quantity', 'price', 'price_rrc']
                for field in required_item_fields:
                    if field not in item:
                        raise KeyError(f"Отсутствует поле в товаре: {field}")

                # Проверка типов данных
                if not isinstance(item['quantity'], int) or item['quantity'] <= 0:
                    raise ValueError(f"Некорректное количество: {item['quantity']}")

                # Создание/обновление продукта
                product, _ = Product.objects.get_or_create(
                    name=item['name'],
                    defaults={'category': item['category']}
                )

                # Создание/обновление информации о продукте
                product_info = ProductInfo.objects.create(
                    product=product,
                    shop=shop,
                    model=item['model'],
                    quantity=item['quantity'],
                    price=item['price'],
                    price_rrc=item['price_rrc'],
                    external_id=item['id']
                )

                # Обработка параметров
                if 'parameters' in item:
                    for name, value in item['parameters'].items():
                        parameter, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(
                            product_info=product_info,
                            parameter=parameter,
                            value=value
                        )

        return {'Status': True, 'Message': 'Данные успешно импортированы'}

    except requests.exceptions.RequestException as e:
        logger.error(f"Сетевая ошибка: {str(e)}", exc_info=True)
        if self.request.retries < self.max_retries:
            self.retry(exc=e, countdown=2 ** self.request.retries)
        return {'Status': False, 'Error': f'Сетевая ошибка: {str(e)}'}

    except Exception as e:
        logger.error(f"Ошибка импорта: {str(e)}", exc_info=True)

        # Фатальные ошибки (неверные данные)
        if isinstance(e, (KeyError, ValueError, TypeError)):
            return {'Status': False, 'Error': str(e)}

        # Повторные попытки для временных ошибок
        if self.request.retries < self.max_retries:
            self.retry(exc=e, countdown=2 ** self.request.retries)

        return {'Status': False, 'Error': f'Импорт не удался после {self.max_retries} попыток: {str(e)}'}


@shared_task(bind=True, max_retries=3)
def do_export(self, shop_id):
    """
    Экспорт данных магазина в YAML-файл с обработкой ошибок и повторными попытками

    Args:
        self: Экземпляр задачи Celery
        shop_id: ID магазина для экспорта
    """
    try:
        # Проверка входных данных
        if not shop_id:
            raise ValueError("Не указан ID магазина")

        # Получение магазина с обработкой исключений
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            return {
                'Status': False,
                'Error': f'Магазин с ID {shop_id} не найден',
                'Code': 'SHOP_NOT_FOUND'
            }

        # Сбор данных магазина
        user = shop.user
        data = {
            'user_id': user.id,
            'shop': shop.name,
            'categories': [],
            'goods': []
        }

        # Экспорт категорий
        categories = Category.objects.filter(shops=shop).prefetch_related('shops')
        for category in categories:
            data['categories'].append({
                'id': category.id,
                'name': category.name
            })

        # Экспорт товаров
        product_infos = ProductInfo.objects.filter(shop=shop).select_related(
            'product', 'product__category'
        ).prefetch_related('product_parameters__parameter')

        for product_info in product_infos:
            product = product_info.product
            goods_data = {
                'name': product.name,
                'category_id': product.category_id,
                'model': product_info.model,
                'quantity': product_info.quantity,
                'price': product_info.price,
                'price_rrc': product_info.price_rrc,
                'id': product_info.external_id,
                'parameters': {}
            }

            # Экспорт параметров товара
            for param in product_info.product_parameters.all():
                goods_data['parameters'][param.parameter.name] = param.value

            data['goods'].append(goods_data)

        # Подготовка и сохранение YAML
        yaml_file_path = f"exports/{shop.name}_export.yaml"

        try:
            # 8. Проверка доступности пути
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile

            if not default_storage.exists('exports/'):
                default_storage.makedirs('exports/')

            # Сохранение файла
            yaml_content = yaml.dump(data, allow_unicode=True, Dumper=yaml.SafeDumper)
            default_storage.save(yaml_file_path, ContentFile(yaml_content))

            return {
                'Status': True,
                'Message': 'Данные успешно экспортированы',
                'File': yaml_file_path,
                'ExportedAt': timezone.now().isoformat()
            }

        except Exception as storage_error:
            logger.error(f'Ошибка сохранения файла: {str(storage_error)}', exc_info=True)
            return {
                'Status': False,
                'Error': f'Не удалось сохранить файл: {str(storage_error)}',
                'Code': 'FILE_SAVE_FAILED'
            }

    except Exception as e:
        logger.error(f'Критическая ошибка экспорта: {str(e)}', exc_info=True)

        # Повторные попытки для временных ошибок
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 10  # Экспоненциальная задержка
            return self.retry(exc=e, countdown=countdown)

        return {
            'Status': False,
            'Error': f'Экспорт не удался после {self.max_retries} попыток: {str(e)}',
            'Code': 'EXPORT_FAILED'
        }
