import json

import jwt
from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from django.db.models import Q, F, Sum
from django.http import JsonResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from backend.models import Category, Shop, ProductInfo, Order, OrderItem, Contact
from backend.serializers import CategorySerializer, ShopSerializer, ProductInfoSerializer, OrderItemSerializer, \
    OrderSerializer, ContactSerializer, UserSerializer, CustomTokenObtainPairSerializer
from backend.signals import new_order
from backend.tasks import do_import, send_email
from backend.utils import string_to_bool
from .utils import AccessMixin


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterAccount(APIView):
    """
    Класс для регистрации пользователя
    """

    @swagger_auto_schema(
        operation_description="Регистрация нового пользователя",
        request_body=UserSerializer,
        responses={
            201: openapi.Response(
                description="Успешная регистрация",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh-токен'),
                        'access': openapi.Schema(type=openapi.TYPE_STRING, description='Access-токен'),
                    },
                )
            ),
            400: 'Ошибка регистрации',
            403: 'Неавторизованный пользователь'
        }
    )
    def post(self, request: Request, *args, **kwargs):
        """
        Регистрация нового пользователя

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом регистрации
        """

        # Проверка обязательных полей
        if not all(field in request.data for field in
                   ['first_name', 'last_name', 'email', 'password', 'company', 'position']):
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=400)

        # Валидация пароля
        try:
            validate_password(request.data['password'])
        except Exception as password_error:
            return JsonResponse({'Status': False,
                                 'Errors': str(password_error)},
                                status=400)

        # Проверка уникальности email
        user_serializer = UserSerializer(data=request.data)
        if user_serializer.is_valid():
            # создаём пользователя
            user = user_serializer.save()
            user.set_password(request.data['password'])
            user.save()
            refresh = RefreshToken.for_user(user)
            return JsonResponse({'refresh': str(refresh),
                                 'access': str(refresh.access_token)})
        else:
            return JsonResponse({'Status': False,
                                 'Errors': user_serializer.errors})


class ConfirmAccount(APIView):
    """
    Класс для подтверждения аккаунта
    """

    @swagger_auto_schema(
        operation_description="Подтверждение почтового адреса",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'token'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL,
                                        description='Почтовый адрес'),
                'token': openapi.Schema(type=openapi.TYPE_STRING, description='Токен подтверждения')
            }
        ),
        responses={
            200: 'Email успешно подтвержден',
            400: 'Неправильно указан email или token',
            403: 'Неавторизованный пользователь'
        }
    )
    def post(self, request: Request, *args, **kwargs):
        """
        Подтверждение почтового адреса

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом подтверждения
        """

        # Проверка обязательных полей
        if {'email', 'token'}.issubset(request.data):
            email = request.data['email']
            token = request.data['token']

            try:
                decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                user_email = decoded_token.get('email')

                if user_email == email:
                    user = User.objects.get(email=email)
                    user.is_active = True
                    user.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': 'Неправильно указан email или token'})
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан email или token'})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class AccountDetails(APIView, AccessMixin):
    """
    Класс для получения и обновления данных аккаунта пользователя
    """

    @swagger_auto_schema(
        responses={200: UserSerializer, 403: 'Неавторизованный пользователь'}
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Получение данных аккаунта пользователя

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с данными аккаунта пользователя
        """

        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        # Проверка наличия обязательных полей
        if 'password' in request.data:
            # Проверка пароля на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                return JsonResponse({'Status': False, 'Errors': str(password_error)}, status=400)

            # Установка нового пароля
            request.user.set_password(request.data['password'])

        # Проверка наличия остальных обязательных полей
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors}, status=400)


class LoginView(APIView, AccessMixin):
    """
    Класс для авторизации пользователя
    """

    @swagger_auto_schema(
        operation_description="Авторизация пользователя",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL,
                                        description='Почтовый адрес'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль')
            }
        ),
        responses={
            200: 'Успешная авторизация',
            400: 'Неправильно указан email или пароль',
            403: 'Неавторизованный пользователь'
        }
    )
    def post(self, request: Request, *args, **kwargs):
        """
        Авторизация пользователя

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом авторизации
        """

        # Проверка обязательных полей
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(email=request.data['email'], password=request.data['password'])
            if user is not None:
                refresh = RefreshToken.for_user(user)
                return JsonResponse({'Status': True,
                                     'Refresh': str(refresh),
                                     'Access': str(refresh.access_token)
                                     })
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан email или пароль'})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class CategoryView(ListAPIView):
    """
    Класс для получения списка категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @swagger_auto_schema(
        operation_description="Получение списка категорий",
        responses={200: CategorySerializer(many=True),
                   403: 'Неавторизованный пользователь'}
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Получение списка категорий

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с списком категорий
        """
        return super().get(request, *args, **kwargs)


class ShopView(ListAPIView):
    """
    Класс для получения списка магазинов
    """
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer

    @swagger_auto_schema(
        responses={200: ShopSerializer(many=True), 403: 'Неавторизованный пользователь'}
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Получение списка магазинов
        
        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с списком магазинов
        """
        return super().get(request, *args, **kwargs)


class ProductInfoView(APIView):
    """
    Класс для получения информации о продукте
    """

    @swagger_auto_schema(
        operation_description="Получение информации о продукте с фильтрацией",
        manual_parameters=[
            openapi.Parameter('shop_id', openapi.IN_QUERY,
                              description='ID магазина',
                              required=False,
                              type=openapi.TYPE_INTEGER),
            openapi.Parameter('category_id', openapi.IN_QUERY,
                              description='ID категории',
                              required=False,
                              type=openapi.TYPE_INTEGER)
        ],
        responses={
            200: ProductInfoSerializer(many=True),
            403: 'Неавторизованный пользователь'
        }
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Получение информации о продукте с фильтрацией

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с информацией о продукте
        """
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(category_id=category_id)

        # Фильтруем и убираем дубликаты        
        queryset = ProductInfo.objects.filter(query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        # Сериализуем данные
        serializer = ProductInfoSerializer(queryset, many=True)
        return Response(serializer.data)


class BasketView(APIView, AccessMixin):
    """
    Класс для работы с корзиной
    """

    @swagger_auto_schema(
        operation_description="Получение корзины пользователя",
        responses={
            200: OrderItemSerializer(many=True),
            403: 'Неавторизованный пользователь'
        }
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Получение корзины пользователя

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с корзиной пользователя
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        basket = Order.objects.filter(
            user_id=request.user.id, status='basket').select_related('user', 'contact').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        # Сериализируем данные
        serializer = OrderItemSerializer(basket, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Добавление товаров в корзину",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['items'],
            properties={
                'items': openapi.Schema(
                    type=openapi.TYPE_ARRAY, description='JSON-строка с элементами корзины',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'product_info': openapi.Schema(
                                type=openapi.TYPE_INTEGER, description='ID продукта'
                            ),
                            'quantity': openapi.Schema(
                                type=openapi.TYPE_INTEGER, description='Количество'
                            )
                        }
                    ),
                )
            },
            responses={
                200: openapi.Response(
                    description='Товары успешно добавлены в корзину',
                    schema=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'Status': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Статус выполнения задачи'),
                            'Создано объектов': openapi.Schema(type=openapi.TYPE_INTEGER,
                                                               description='Количество созданных объектов')
                        }
                    )
                ),
                400: 'Ошибка добавления товаров в корзину',
                403: 'Неавторизованный пользователь'
            }
        ),
    )
    def post(self, request: Request, *args, **kwargs):
        """
        Добавление товара в корзину
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        items_ids = request.data.get('items')
        if items_ids:
            try:
                items_dict = json.loads(items_ids)
            except ValueError:
                return JsonResponse({'Status': False, 'Error': 'Некорректный формат данных'})
            else:
                basket, _ = Order.objects.get_or_create(user=request.user.id, status='basket')
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                            objects_created += 1
                        except IntegrityError:
                            return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
                    else:
                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

                return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    @swagger_auto_schema(
        operation_description="Удаление товара из корзины",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['items'],
            properties={
                'items': openapi.Schema(
                    type=openapi.TYPE_STRING, description='JSON-строка с элементами корзины',
                )
            },
        ),
        responses={
            200: openapi.Response(
                description='Товары успешно удалены из корзины',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'Status': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Статус выполнения задачи'),
                        'Удалено объектов': openapi.Schema(type=openapi.TYPE_INTEGER,
                                                           description='Количество удаленных объектов')
                    }
                )
            ),
            400: 'Ошибка удаления товаров из корзины',
            403: 'Неавторизованный пользователь'
        }
    )
    def delete(self, request: Request, *args, **kwargs):
        """
        Удаление товара из корзины

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом удаления товара из корзины
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        items_ids = request.data.get('items')
        if items_ids:
            items_list = items_ids.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
            query = Q()
            objects_deleted = 0
            for item_id in items_list:
                if item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=item_id)
                    objects_deleted = True
            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    @swagger_auto_schema(
        operation_description="Обновление количества товара в корзине",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['items'],
            properties={
                'items': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='JSON строка с элементами корзины для обновления',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID товара'),
                            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Новое количество товара')
                        }
                    )
                )
            }
        ),
        responses={
            200: openapi.Response(
                description='Успешное обновление количества товаров в корзине',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'Status': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Статус выполнения задачи'),
                        'Обновлено объектов': openapi.Schema(type=openapi.TYPE_INTEGER,
                                                             description='Количество обновленных объектов')
                    }
                )
            ),
            400: 'Ошибка обновления количества товаров в корзине',
            403: 'Неавторизованный пользователь'
        }
    )
    def put(self, request: Request, *args, **kwargs):
        """
        Обновление количества товара в корзине

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом обновления количества товара в корзине
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        items_ids = request.data.get('items')
        if items_ids:
            try:
                items_dict = json.loads(items_ids)
            except ValueError:
                return JsonResponse({'Status': False, 'Error': 'Некорректный формат данных'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
                objects_updated = 0
                for order_item in items_dict:
                    if type(order_item['id']) == int and type(order_item['quantity']) == int:
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])
                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerUpdate(APIView, AccessMixin):
    """
    Класс для обновления информации о партнере
    """

    @swagger_auto_schema(
        operation_description='Получение информации о партнере',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['url'],
            properties={
                'url': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI,
                                      description='URL для обновления прайса')
            }
        ),
        responses={
            200: openapi.Response(
                description='Задача на обновление прайса успешно создана',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'Status': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Статус выполнения задачи'),
                        'Task': openapi.Schema(type=openapi.TYPE_STRING, description='ID задачи'),
                        'Task ID': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID задачи')
                    }
                )
            ),
            400: 'Неверный URL',
            403: 'Неавторизованный пользователь'
        }
    )
    def post(self, request: Request, *args, **kwargs):
        """
        Обновление прайса от поставщика

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом обновления прайса от поставщика
        """
        access_response = self.check_shop_access(request) and self.check_auth(request)
        if access_response:
            return access_response

        url = request.data.get('url')
        if url:
            task = do_import.delay(url)
            return JsonResponse({'Status': True, 'Task': str(task), 'Task ID': task.id})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerState(APIView, AccessMixin):
    """
    Класс для управления статусом партнера
    """

    @swagger_auto_schema(
        responses={200: ShopSerializer, 403: 'Неавторизованный пользователь'}
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Получение статуса партнера

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом получения статуса партнера
        """
        access_response = self.check_shop_access(request) and self.check_auth(request)
        if access_response:
            return access_response

        shop = request.user.shop
        if not shop:
            return JsonResponse({'Status': False, 'Error': 'Магазин не найден'}, status=404)
        else:
            serializer = ShopSerializer(shop)
            return Response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'state': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Статус партнера')
            },
            responses={200: 'Успешное обновление статуса партнера', 400: 'Ошибка обновления статуса партнера',
                       403: 'Неавторизованный пользователь'}
        ),
    )
    def post(self, request: Request, *args, **kwargs):
        """
        Обновление статуса партнера

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом обновления статуса партнера
        """
        access_response = self.check_shop_access(request) and self.check_auth(request)
        if access_response:
            return access_response

        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=string_to_bool(state))
                return JsonResponse({'Status': True})
            except ValueError as e:
                return JsonResponse({'Status': False, 'Errors': str(e)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView, AccessMixin):
    """
    Класс для получения заказов партнера
    """

    @swagger_auto_schema(
        responses={200: OrderSerializer(many=True), 403: 'Неавторизованный пользователь'}
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Получение заказов партнера

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом получения заказов партнера
        """
        access_response = self.check_shop_access(request) and self.check_auth(request)
        if access_response:
            return access_response

        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        # Сериализуем данные
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ContactView(APIView, AccessMixin):
    """
    Класс для работы с контактами
    """

    @swagger_auto_schema(
        operation_description='Получение контактов пользователя',
        responses={
            200: ContactSerializer(many=True),
            403: 'Неавторизованный пользователь'
        }
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Получение контактов пользователя

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом получения контактов пользователя
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        contact = Contact.objects.filter(user_id=request.user.id).all()
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description='Добавление контактной информации',
        request_body=ContactSerializer,
        responses={
            200: 'Успешное добавление контакта',
            400: 'Ошибка добавления контакта',
            403: 'Неавторизованный пользователь'
        }
    )
    def post(self, request: Request, *args, **kwargs):
        """
        Добавление новой контактной информации

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом добавления контакта
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        if {'city', 'street', 'phone'}.issubset(request.data):
            request.data._mutable = True
            request.data.update({'user': request.user.id})
            serializer = ContactSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    @swagger_auto_schema(
        operation_description='Обновление контактной информации',
        request_body=ContactSerializer,
        responses={
            200: 'Успешное обновление контактной информации',
            400: 'Ошибка обновления контактной информации',
            403: 'Неавторизованный пользователь'
        }
    )
    def put(self, request: Request, *args, **kwargs):
        """
        Обновление контактной информации

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом обновления контактной информации
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        if 'id' in request.data:
            if request.data['id'].isdigit():
                contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                if contact:
                    serializer = ContactSerializer(contact, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True})
                    else:
                        return JsonResponse({'Status': False, 'Errors': serializer.errors})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    @swagger_auto_schema(
        operation_description='Удаление контактной информации',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['items'],
            properties={
                'items': openapi.Schema(type=openapi.TYPE_STRING, description='Список ID контактов для удаления')
            },
        ),
        responses={
            200: openapi.Response(
                description='Контактная информация успешно удалена',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'Status': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Статус выполнения задачи'),
                        'Удалено объектов': openapi.Schema(type=openapi.TYPE_INTEGER,
                                                           description='Количество удаленных объектов')
                    }
                )
            ),
            400: 'Ошибка удаления контактов',
            403: 'Неавторизованный пользователь'
        }
    )
    def delete(self, request: Request, *args, **kwargs):
        """
        Удаление контактной информации

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом удаления контактной информации
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        items_ids = request.data.get('items')
        if items_ids:
            items_list = items_ids.split(',')
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True
            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class OrderView(APIView, AccessMixin):
    """
    Класс для работы с заказами
    """

    @swagger_auto_schema(
        operation_description='Получение заказов пользователя',
        responses={
            200: OrderSerializer(many=True),
            403: 'Неавторизованный пользователь'
        }
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Получение заказов пользователя
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        order = Order.objects.filter(
            user_id=request.user.id).exclude(status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description='Размещение заказа из корзины',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id', 'contact'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID корзины'),
                'contact': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID контакта')
            }
        ),
        responses={
            200: 'Заказ успешно размещен',
            400: 'Ошибка размещения заказа',
            403: 'Неавторизованный пользователь'
        }
    )
    def post(self, request: Request, *args, **kwargs):
        """
        Размещение заказа из корзины
        """
        auth_response = self.check_auth(request)
        if auth_response:
            return auth_response

        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data['id']).update(
                        contact_id=request.data['contact'], status='new')
                except IntegrityError as error:
                    return JsonResponse({'Status': False, 'Errors': str(error)})
                else:
                    if is_updated:
                        new_order.send(sender=self.__class__, user_id=request.user.id)
                        return JsonResponse({'Status': True})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class SendEmailView(APIView):
    """
    Класс для отправки электронной почты
    """

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'recipient_list': openapi.Schema(
                    type=openapi.TYPE_ARRAY,  # Указываем, что это массив
                    items=openapi.Schema(type=openapi.TYPE_STRING),  # Тип элементов массива (строки)
                    description='Список получателей'
                ),
                'subject': openapi.Schema(type=openapi.TYPE_STRING, description='Тема письма'),
                'message': openapi.Schema(type=openapi.TYPE_STRING, description='Текст письма'),
                'from_email': openapi.Schema(type=openapi.TYPE_STRING, description='Email отправителя'),
            },
        ),
        responses={
            200: 'Успешное отправление электронной почты',
            400: 'Ошибка отправления электронной почты',
            403: 'Неавторизованный пользователь'
        }
    )
    def post(self, request: Request, *args, **kwargs):
        """
        Отправка электронной почты с использованием Celery

        Args:
            request: HTTP-запрос
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом отправки электронной почты
        """
        subject = request.data.get('subject')
        message = request.data.get('message')
        from_email = request.data.get('from_email')
        recipient_list = request.data.get('recipient_list', [])

        if subject and message and from_email and recipient_list:
            task = send_email.delay(subject, message, from_email, recipient_list)
            return JsonResponse({'Status': True, 'Task': str(task), 'Task ID': task.id})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class TaskStatusView(APIView):
    """
    Класс для получения статуса задачи
    """

    @swagger_auto_schema(
        responses={200: 'Успешное получение статуса задачи', 403: 'Неавторизованный пользователь'}
    )
    def get(self, request: Request, task_id: str, *args, **kwargs):
        """
        Получение статуса задачи

        Args:
            request: HTTP-запрос
            task_id: ID задачи
            *args: Дополнительные аргументы
            **kwargs: Дополнительные аргументы

        Returns:
            JsonResponse: JSON-ответ с результатом получения статуса задачи
        """
        task_result = AsyncResult(task_id)
        result = {
            'task_id': task_id,
            'task_status': task_result.status,
            'task_result': task_result.result
        }
        return JsonResponse(result)
