import logging
import os

import requests
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from requests import RequestException

from backend.models import ProductInfo, Shop, Category, Parameter, ProductParameter, Product, User
import yaml
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

        if not validate_url(url):
            raise ValidationError("Неверный URL")

        if user_id is None:
            raise ValueError('Пользователь не указан')
        try:
            user = User.objects.get(id=user_id, user_type='shop')
        except ObjectDoesNotExist:
            raise ValueError("Пользователь не найден или не является магазином")

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
        except RequestException as e:
            return JsonResponse({'status': False, 'Ошибка загрузки данных': str(e)})

        data = yaml.safe_load(response.content)

        required_fields = ['shop', 'categories', 'goods']
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Отсутствует обязательное поле: {field}")

        # Создаем/обновляем магазин
        shop, created = Shop.objects.get_or_create(name=data['shop'], defaults={'user': user})
        if not created and shop.user != user:
            raise PermissionError("Этот магазин принадлежит другому пользователю")

        # Обработка категорий
        for category_data in data['categories']:
            Category.objects.get_or_create(
                id=category_data['id'],
                defaults={'name': category_data['name']}
            )

        # Обработка товаров
        with transaction.atomic():
            ProductInfo.objects.filter(shop=shop).delete()

            for item in data['goods']:
                # Проверка обязательных полей
                required_item_fields = ['id', 'category', 'model', 'quantity', 'price', 'price_rrc', 'name']
                for field in required_item_fields:
                    if field not in item:
                        raise KeyError(f"Отсутствует поле в товаре: {field}")

                # Получаем категорию как объект
                category_id = item['category']
                try:
                    category = Category.objects.get(id=category_id)
                except Exception:
                    logger.warning(f"Категория с ID {category_id} не найдена")
                    continue

                # Создаем продукт
                product, _ = Product.objects.get_or_create(
                    name=item['name'],
                    defaults={'category': category}
                )
                if product.category != category:
                    product.category = category
                    product.save()

                # Создаем информацию о товаре
                product_info = ProductInfo.objects.create(
                    product=product,
                    shop=shop,
                    model=item['model'],
                    external_id=item['id'],
                    price=item['price'],
                    price_rrc=item['price_rrc'],
                    quantity=item['quantity']
                )

                # Добавляем параметры
                if 'parameters' in item:
                    for name, value in item['parameters'].items():
                        parameter, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(
                            product_info=product_info,
                            parameter=parameter,
                            value=value
                        )

        return {'Status': True}

    except requests.RequestException as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        if self.request.retries < self.max_retries:
            self.retry(exc=e, countdown=2 ** self.request.retries)
        return {'Status': False, 'Error': f'Не удалось загрузить файл: {str(e)}'}

    except yaml.YAMLError as e:
        logger.error(f"Ошибка парсинга YAML: {e}")
        return {'Status': False, 'Error': 'Файл имеет неверный формат YAML'}

    except Exception as e:
        logger.error(f"Критическая ошибка импорта: {e}", exc_info=True)
        return {'Status': False, 'Error': str(e)}


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

        # Подготовка пути к файлу
        yaml_file_path = f"export_data/{shop.name}_export.yaml"
        export_path = os.path.join(settings.MEDIA_ROOT, 'export_data')

        # Проверка существования директории и создание при необходимости
        if not default_storage.exists('export_data/'):
            try:
                os.makedirs(export_path, exist_ok=True)
            except Exception as e:
                logger.error(f"Не удалось создать директорию export_data: {e}")
                return {
                    'Status': False,
                    'Error': 'Не удалось создать директорию для сохранения файла',
                    'Code': 'DIRECTORY_CREATE_FAILED'
                }

        # Преобразование данных в YAML
        try:
            yaml_content = yaml.dump(data, allow_unicode=True, Dumper=yaml.SafeDumper)
        except Exception as e:
            logger.error(f"Ошибка сериализации в YAML: {e}")
            return {
                'Status': False,
                'Error': 'Ошибка преобразования данных в формат YAML',
                'Code': 'YAML_SERIALIZE_ERROR'
            }

        # Сохранение файла
        try:
            default_storage.save(yaml_file_path, ContentFile(yaml_content.encode('utf-8')))
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            return {
                'Status': False,
                'Error': 'Не удалось сохранить файл',
                'Code': 'FILE_SAVE_FAILED'
            }

        return {
            'Status': True,
            'Message': 'Данные успешно экспортированы',
            'File': yaml_file_path,
            'ExportedAt': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f'Критическая ошибка экспорта: {str(e)}', exc_info=True)

        # Повторные попытки для временных ошибок
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 10  # экспоненциальная задержка
            return self.retry(exc=e, countdown=countdown)

        return {
            'Status': False,
            'Error': f'Экспорт не удался после {self.max_retries} попыток: {str(e)}',
            'Code': 'EXPORT_FAILED'
        }
