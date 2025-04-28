import logging
from celery import shared_task
from celery.exceptions import Retry
from django.core.mail import EmailMultiAlternatives
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
# from django.core.files.base import ContentFile
# from django.core.files.storage import default_storage
from backend.models import ProductInfo, Shop, Category, Parameter, ProductParameter, Product, User
# import yaml
from yaml import load as load_yaml, Loader
from requests import get

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
def do_import(self, url):
    """
    Импорт данных из YAML-файла

    Args:
        self: Экземпляр задачи Celery
        url: URL-адрес YAML-файла
    """
    try:
        if not url:
            raise ValueError("URL не указан")

        # Валидация URL
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            raise ValueError(f"Неверный URL: {str(e)}")

        # Получение данных
        response = get(url)
        if response.status_code != 200:
            raise ConnectionError(f"Ошибка при получении данных: {response.status_code}")

        stream = response.content
        data = load_yaml(stream, Loader=Loader)

        # Проверка наличия необходимых данных
        required_fields = ['user_id', 'shop', 'categories', 'goods']
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Отсутствует обязательное поле: {field}")

        user = User.objects.get(id=data['user_id'], user_type='shop')
        shop, _ = Shop.objects.get_or_create(
            name=data['shop'],
            user=user
        )

        # Обработка категорий
        for category in data['categories']:
            category_object, _ = Category.objects.get_or_create(
                id=category['id'],
                name=category['name']
            )
            category_object.shops.add(shop.id)
            category_object.save()

        # Очистка старых данных
        ProductInfo.objects.filter(shop_id=shop.id).delete()

        # Импорт товаров
        for item in data['goods']:
            product, _ = Product.objects.get_or_create(
                name=item['name'],
                category_id=item['category_id']
            )

            product_info = ProductInfo.objects.create(
                product_id=product.id,
                shop_id=shop.id,
                model=item['model'],
                quantity=item['quantity'],
                price=item['price'],
                price_rrc=item['price_rrc'],
                external_id=item['id']
            )

            # Обработка параметров товара
            for name, value in item['parameters'].items():
                parameter, _ = Parameter.objects.get_or_create(name=name)

                ProductParameter.objects.create(
                    product_info_id=product_info.id,
                    parameter_id=parameter.id,
                    value=value
                )

        return {'Status': True, 'Message': 'Данные успешно импортированы'}

    except Exception as e:
        # Логирование ошибки
        logger.error(f'Ошибка импорта данных: {e}', exc_info=True)

        # Если количество попыток исчерпано
        if self.request.retries >= self.max_retries:
            return {'Status': False, 'Error': f'Импорт не удался после {self.max_retries} попыток: {str(e)}'}

        # Повторная попытка
        try:
            countdown = 2 ** self.request.retries
            self.retry(exc=e, countdown=countdown)
        except Retry as retry_exc:
            raise retry_exc

# @shared_task
# def do_export(shop_id):
#     """
#     Экспорт данных в YAML-файл
#
#     Args:
#         shop_id: ID магазина, данные которого нужно экспортировать
#     """
#     try:
#         shop = Shop.objects.get(id=shop_id)
#         user = shop.user
#
#         data = {
#             'user_id': user.id,
#             'shop': shop.name,
#             'categories': [],
#             'goods': []
#         }
#
#         # Собираем категории
#         categories = Category.objects.filter(shops=shop)
#         for category in categories:
#             data['categories'].append({
#                 'id': category.id,
#                 'name': category.name
#             })
#
#         # Собираем товары
#         product_infos = ProductInfo.objects.filter(shop=shop)
#         for product_info in product_infos:
#             product = product_info.product
#             goods_data = {
#                 'name': product.name,
#                 'category_id': product.category_id,
#                 'model': product_info.model,
#                 'quantity': product_info.quantity,
#                 'price': product_info.price,
#                 'price_rrc': product_info.price_rrc,
#                 'id': product_info.external_id,
#                 'parameters': {}
#             }
#
#             # Собираем параметры товара
#             product_parameters = ProductParameter.objects.filter(product_info=product_info)
#             for param in product_parameters:
#                 goods_data['parameters'][param.parameter.name] = param.value
#
#             data['goods'].append(goods_data)
#
#         # Сохраняем данные в YAML-файл
#         yaml_file_path = f"exports/{shop.name}_export.yaml"
#         yaml_content = yaml.dump(data, allow_unicode=True)
#
#         # Сохраняем файл в файловую систему
#         default_storage.save(yaml_file_path, ContentFile(yaml_content))
#
#         return {'Status': True, 'Message': 'Данные успешно экспортированы', 'File': yaml_file_path}
#     except Exception as e:
#         logger.error(f'Ошибка экспорта данных: {e}', exc_info=True)
#         return {'Status': False, 'Error': str(e)}
