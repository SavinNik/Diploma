from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core import mail
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from backend.models import Shop, Product, ProductInfo, Order, OrderItem, Contact, Category
from backend.serializers import ProductInfoSerializer, UserSerializer
from backend.tasks import send_email
from backend.utils import get_password_reset_token

User = get_user_model()


class UserRegistrationTestCase(TestCase):
    """
    Тестирование регистрации пользователя
    """

    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.url = reverse('user-register')

    def test_user_registration(self):
        """
        Тестирование регистрации пользователя
        """
        data = {
            'first_name': 'Nik',
            'last_name': 'Sav',
            'email': 'niksav@gmail.com',
            'password': 'very_strong_password',
            'company': 'Google',
            'position': 'Software Engineer'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=data['email']).exists())

    def test_user_registration_invalid_password(self):
        """
        Тестирование регистрации пользователя с недостаточно сложным паролем
        """
        data = {
            'first_name': 'Nik',
            'last_name': 'Sav',
            'email': 'niksav@gmail.com',
            'password': 'foo',
            'company': 'Google',
            'position': 'Software Engineer'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Error", response.data)
        self.assertFalse(User.objects.filter(email=data['email']).exists())

    def test_user_registration_invalid_email(self):
        """
        Тестирование регистрации пользователя с неправильным адресом электронной почты
        """
        data = {
            'first_name': 'Nik',
            'last_name': 'Sav',
            'email': 'niksavgmail.com',
            'password': 'very_strong_password',
            'company': 'Google',
            'position': 'Software Engineer'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Error", response.data)
        self.assertFalse(User.objects.filter(email=data['email']).exists())

    def test_duplicate_email(self):
        """
        Тестирование регистрации пользователя с уже существующим адресом электронной почты
        """
        User.objects.create_user(
            email='niksav@gmail.com',
            password='very_strong_password',
        )
        data = {
            'first_name': 'Nik',
            'last_name': 'Sav',
            'email': 'niksav@gmail.com',
            'password': 'very_strong_password',
            'company': 'Google',
            'position': 'Software Engineer'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Error", response.data)
        self.assertFalse(User.objects.filter(email=data['email']).exists())


class UserLoginTestCase(TestCase):
    """
    Тестирование авторизации пользователя
    """

    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.url = reverse('user-login')
        self.user = User.objects.create_user(
            email='niksav@gmail.com',
            password='very_strong_password',
            first_name='Nik',
            last_name='Sav',
            company='Google',
            position='Software Engineer'
        )

    def test_user_login(self):
        """
        Тестирование авторизации пользователя
        """
        data = {
            'email': 'niksav@gmail.com',
            'password': 'very_strong_password'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Token", response.json())

    def test_user_login_invalid_password(self):
        """
        Тестирование авторизации пользователя с неправильным паролем
        """
        data = {
            'email': 'niksav@gmail.com',
            'password': 'foo'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Error", response.data)

    def test_login_with_inactive_user(self):
        """
        Тестирование авторизации пользователя с неактивным пользователем
        """
        self.user.is_active = False
        self.user.save()
        data = {
            'email': 'niksav@gmail.com',
            'password': 'very_strong_password'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Error", response.data)

    def test_login_missing_fields(self):
        """
        Тестирование авторизации без обязательных полей
        """
        data = {
            'email': 'niksav@gmail.com'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Error", response.data)


class ConfirmEmailTestCase(TestCase):
    """
    Тестирование подтверждения электронной почты
    """

    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='confim@gmail.com',
            password='password',
            is_active=False
        )
        self.url = reverse('user-confirm-email')
        self.token = default_token_generator.make_token(self.user)

    def test_confirm_valid_email(self):
        """
        Подтверждение электронной почты с валидным токеном
        """
        data = {
            'email': self.user.email,
            'token': self.token
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.get(email=self.user.email).is_active)

    def test_confirm_invalid_email(self):
        """
        Подтверждение электронной почты с невалидным токеном
        """
        data = {
            'email': self.user.email,
            'token': 'invalid_token'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.get(email=self.user.email).is_active)


class PasswordResetTestCase(TestCase):
    """
    Тестирование сброса пароля
    """
    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.reset_url = reverse('password-reset')
        self.confirm_reset_url = reverse('password-reset-confirm')
        self.user = User.objects.create_user(
            email='reset@gmail.com',
            password='very_strong_password'
        )

    def test_password_reset_request(self):
        """
        Тестирование запроса на сброс пароля
        """
        response =self.client.post(self.reset_url, {'email': self.user.email}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Token", response.json())

    def test_password_reset_confirm(self):
        """
        Установка нового пароля через токен
        """
        token = get_password_reset_token(self.user)
        data = {
            'token': token,
            'password': 'newpassword'
        }
        response = self.client.post(self.confirm_reset_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.get(email=self.user.email).check_password(data['password']))


class UserSerializerTestCase(TestCase):
    """
    Тестирование сериализатора пользователя
    """
    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.user_data = {
            'email': 'buyer@gmail.com',
            'password': 'very_strong_password',
            'first_name': 'Buyer',
            'last_name': 'Buyer',
            'company': 'BuyerCompany',
            'position': 'Buyer'
    }

    def test_serializer_valid_data(self):
        """
        Тестирование сериализатора с валидными данными
        """
        serializer = UserSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.email, self.user_data['email'])

    def test_serializer_invalid_email(self):
        """
        Тестирование сериализатора с невалидными данными
        """
        self.user_data['email'] = 'invalid_email'
        serializer = UserSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)


class PermissionTestCase(TestCase):
    """
    Тестирование прав доступа
    """

    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            email='buyer@gmail.com',
            password='very_strong_password',
            user_type='buyer'
        )
        self.shop = User.objects.create_user(
            email='shop@gmail.com',
            password='very_strong_password',
            user_type='shop'
        )
        self.admin = User.objects.create_superuser(
            email='admin@gmail.com',
            password='very_strong_password'
        )

    def test_partner_update_permissions(self):
        """
        Тестирование прав доступа для обновления прайса партнера
        """
        url = reverse('backend:partner-update')
        data = {
            'url': 'https://example.com/shop1.yaml'
        }

        # Попытка доступа без авторизации
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Попытка доступа покупателем
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Доступ магазина
        self.client.force_authenticate(user=self.shop)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Доступ администратора
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_only_endpoints(self):
        """
        Тестирование эндпоинтов, доступных только администратору
        """
        admin_only_urls = [
            '/admin/',
            # Добавьте другие административные URL
        ]

        for url in admin_only_urls:
            # Без авторизации
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # Как покупатель
            self.client.force_authenticate(user=self.buyer)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # Как магазин
            self.client.force_authenticate(user=self.shop)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # Как администратор
            self.client.force_authenticate(user=self.admin)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProductValidationTestCase(TestCase):
    """
    Тестирование валидации данных продукта
    """

    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='shop@gmail.com',
            password='very_strong_password',
            user_type='shop'
        )
        self.client.force_authenticate(user=self.user)
        self.shop = Shop.objects.create(name='Test Shop', user=self.user)
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(name='Test Product', category=self.category)

    def test_product_info_validation(self):
        """
        Тестирование валидации данных при создании информации о продукте
        """
        url = reverse('backend:partner-update')
        invalid_data = {
            'url': 'https://example.com/invalid.yaml'
        }
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Error", response.data)

    def test_quantity_boundary_values(self):
        """
        Тестирование граничных значений quantity
        """
        product_info = ProductInfo.objects.create(
            model='test-model',
            external_id=12345,
            product=self.product,
            shop=self.shop,
            quantity=0,  # Граничное значение
            price=100,
            price_rrc=120
        )

        # Проверка quantity = 0
        serializer = ProductInfoSerializer(product_info)
        self.assertEqual(serializer.data['quantity'], 0)

        # Проверка отрицательного значения
        product_info.quantity = -1
        with self.assertRaises(ValidationError):
            product_info.full_clean()


class ProductImportTestCase(TestCase):
    """
    Тестирование импорта товаров
    """

    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='shop@gmail.com',
            password='very_strong_password',
            user_type='shop'
        )
        self.client.force_authenticate(user=self.user)

    def test_product_import(self):
        """
        Тестирование успешного импорта товаров
        """
        data = {
            'url': 'https://example.com/shop1.yaml'
        }
        response = self.client.post('/api/v1/partner/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Status", response.data)
        self.assertTrue(Shop.objects.filter(name='Связной').exists())
        self.assertTrue(Category.objects.filter(name='Смартфоны').exists())
        self.assertTrue(Product.objects.filter(name='Смартфон Apple iPhone XS Max 512GB (золотистый)').exists())
        self.assertTrue(ProductInfo.objects.filter(model='apple/iphone/xs-max').exists())

    def test_product_import_invalid_url(self):
        """
        Тестирование импорта товаров с неправильным URL
        """
        data = {
            'url': 'invalid_url'
        }
        response = self.client.post('/api/v1/partner/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Error", response.data)


class OrderTestCase(TestCase):
    """
    Тестирование заказа
    """
    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.url = reverse('backend:order')
        self.user = User.objects.create_user(
            email='buyer@gmail.com',
            password='very_strong_password',
            first_name='Buyer',
            last_name='Buyer',
            company='BuyerCompany',
            position='Buyer',
        )
        self.client.force_authenticate(user=self.user)

        # Создаем магазин, категорию, продукт и информацию о продукте
        self.shop = Shop.objects.create(name='Связной', url='https://shop1.com', user=self.user)
        self.category = Category.objects.create(name='Смартфоны')
        self.category.shops.add(self.shop)
        self.product = Product.objects.create(name='Смартфон Apple iPhone XS Max 512GB (золотистый)', category=self.category)
        self.product_info = ProductInfo.objects.create(
            model='apple/iphone/xs-max',
            external_id=4216292,
            product=self.product,
            shop=self.shop,
            quantity=10,
            price=110000,
            price_rrc=120000
        )

        # Создаем контактную информацию для пользователя
        self.contact = Contact.objects.create(
            user=self.user,
            city='Москва',
            street='Улица Ленина',
            house='1',
            phone='1234567890'
        )

        # Создаем заказ и элемент заказа
        self.order = Order.objects.create(user=self.user, status='basket')
        self.order_item = OrderItem.objects.create(order=self.order, product_info=self.product_info, quantity=2)

    def test_create_order(self):
        """
        Тестирование создания заказа
        """
        data = {
            'id': self.order.id,
            'contact': self.contact.id,
        }
        response = self.client.post(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Status", response.data)
        updated_order = Order.objects.get(id=self.order.id)
        self.assertEqual(updated_order.state, 'new')

    def test_create_order_invalid_data(self):
        """
        Тестирование создания заказа с неправильными данными
        """
        data = {
            'id': self.order.id,
            'contact': 111111111,
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Error", response.data)
        updated_order = Order.objects.get(id=self.order.id)
        self.assertEqual(updated_order.state, 'basket')


class BasketTestCase(TestCase):
    """
    Тестирование корзины
    """
    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='buyer@gmail.com',
            password='very_strong_password',
            user_type='buyer'
        )
        self.client.force_authenticate(user=self.user)

        # Создаем магазин, категорию, продукт и информацию о продукте
        self.shop = Shop.objects.create(name='Связной', url='https://shop1.com', user=self.user)
        self.category = Category.objects.create(name='Смартфоны')
        self.product = Product.objects.create(name='Смартфон Apple iPhone XS Max 512GB (золотистый)', category=self.category)
        self.product_info = ProductInfo.objects.create(
            model='apple/iphone/xs-max',
            external_id=4216292,
            product=self.product,
            shop=self.shop,
            quantity=10,
            price=110000,
            price_rrc=120000
        )

    def test_add_to_basket(self):
        """
        Тестирование добавления товара в корзину
        """
        data = {
            'items': [{'product_info': self.product_info.id, 'quantity': 2}]
        }
        response = self.client.post('/api/v1/basket/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Создано объектов', response.data)
        self.assertEqual(response.data['Создано объектов'], 1)

    def test_invalid_quantity(self):
        """
        Тестирование добавления товара в корзину с неправильным количеством
        """
        data = {
            'items': [{'product_info': self.product_info.id, 'quantity': -1}]
        }
        response = self.client.post('/api/v1/basket/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Error', response.data)

    def test_update_basket(self):
        """
        Тестирование обновления количества товара в корзине
        """
        order = Order.objects.create(user=self.user, state='basket')
        order_item = OrderItem.objects.create(order=order, product_info=self.product_info, quantity=2)

        data = {
            'items': [{'id': order_item.id, 'quantity': 3}]
        }
        response = self.client.post('/api/v1/basket/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Обновлено объектов', response.data)
        self.assertEqual(response.data['Обновлено объектов'], 1)
        updated_order_item = OrderItem.objects.get(id=order_item.id)
        self.assertEqual(updated_order_item.quantity, 3)

    def test_delete_from_basket(self):
        """
        Тестирование удаления товара из корзины
        """
        order = Order.objects.create(user=self.user, state='basket')
        order_item = OrderItem.objects.create(order=order, product_info=self.product_info, quantity=2)

        data = {
            'items': str(order_item.id)
        }
        response = self.client.delete('/api/v1/basket/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Удалено объектов', response.data)
        self.assertEqual(response.data['Удалено объектов'], 1)
        self.assertFalse(OrderItem.objects.filter(id=order_item.id).exists())

    def test_basket_permissions(self):
        """
        Тестирование прав доступа к корзине
        """
        # Попытка доступа без авторизации
        self.client.logout()
        response = self.client.post('/api/v1/basket/', format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Error', response.data)

        # Доступ другого пользователя
        other_user = User.objects.create_user(
            email='other_user@gmail.com',
            password='very_strong_password'
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.post('/api/v1/basket/', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Error', response.data)


class ComprehensiveTestCase(TestCase):
    """
    Комплексные тесты с различными сценариями
    """

    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@gmail.com',
            password='very_strong_password'
        )
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(name='Test Product')
        self.shop = Shop.objects.create(name='Test Shop', user=self.user)

    def test_edge_cases(self):
        """
        Тестирование граничных случаев
        """
        # Максимальные значения
        max_values = {
            'quantity': 999999,
            'price': 999999999
        }
        # Минимальные значения
        min_values = {
            'quantity': 1,
            'price': 1
        }

        # Проверка максимальных значений
        product_info = ProductInfo.objects.create(
            model='max-test',
            external_id=999999,
            product=self.product,
            shop=self.shop,
            quantity=max_values['quantity'],
            price=max_values['price'],
            price_rrc=max_values['price'] + 10
        )
        serializer = ProductInfoSerializer(product_info)
        self.assertEqual(serializer.data['quantity'], max_values['quantity'])
        self.assertEqual(serializer.data['price'], max_values['price'])

        # Проверка минимальных значений
        product_info = ProductInfo.objects.create(
            model='min-test',
            external_id=111111,
            product=self.product,
            shop=self.shop,
            quantity=min_values['quantity'],
            price=min_values['price'],
            price_rrc=min_values['price'] + 10
        )
        serializer = ProductInfoSerializer(product_info)
        self.assertEqual(serializer.data['quantity'], min_values['quantity'])
        self.assertEqual(serializer.data['price'], min_values['price'])


class AccessTestCase(TestCase):
    """
    Тестирование прав доступа
    """

    def setUp(self):
        """
        Установка данных для тестирования
        """
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            email='buyer@gmail.com',
            password='very_strong_password',
            user_type='buyer'
        )
        self.shop = User.objects.create_user(
            email='shop@gmail.com',
            password='very_strong_password',
            user_type='shop'
        )

    def test_partner_update_permissions(self):
        """
        Тестирование прав доступа для обновления прайса партнера
        """
        url = '/api/v1/partner/update/'
        data = {
            'url': 'https://example.com/shop1.yaml'
        }

        # Доступ покупателя
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Error', response.data)

        # Доступ магазина
        self.client.force_authenticate(user=self.shop)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SendEmailTestCase(TestCase):
    """
    Тестирование отправки электронной почты
    """
    def test_send_email_task(self):

        send_email.delay('Subject', 'Message', settings.EMAIL_HOST_USER, ['test@gmail.com'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Subject')
        self.assertEqual(mail.outbox[0].body, 'Message')

    def test_send_email_task_failure(self):
        with self.assertRaises(Exception):
            send_email.retry(exc=Exception('SMTP error'), countdown=5)
