from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from backend.models import ProductInfo, Shop, Category, Parameter, ProductParameter, Product
from yaml import load as load_yaml, Loader
from requests import get


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

@shared_task
def do_import(url):
    """
    Импорт данных из YAML-файла

        Args:
            url: URL-адрес YAML-файла
        """
    if url:
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return {'Status': False, 'Error': str(e)}
        else:
            stream = get(url).content
            data = load_yaml(stream, Loader=Loader)
            shop, _ = Shop.objects.get_or_create(
                name=data['shop'], 
                user_id=data['user_id']
            )
            
            for category in data['categories']:
                category_object, _ = Category.objects.get_or_create(
                    id=category['id'], 
                    name=category['name']
                )
                category_object.shops.add(shop.id)
                category_object.save()

            ProductInfo.objects.filter(shop_id=shop.id).delete()
            
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
                
                for name, value in item['parameters'].items():
                    parameter, _ = Parameter.objects.get_or_create(name=name)

                    ProductParameter.objects.create(
                        product_info_id=product_info.id,
                        parameter_id=parameter.id,
                        value=value
                    )
            return {'Status': True, 'Message': 'Данные успешно импортированы'}
    return {'Status': False, 'Error': 'URL не указан'}
                
                        