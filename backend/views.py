import json
from django.db.models import Q, F, Sum
from django.db import IntegrityError
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError 
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from backend.serializers import UserSerializer
from backend.models import ConfirmEmailToken, Category, Shop, ProductInfo, Order, OrderItem, Product, Parameter, ProductParameter, Contact
from backend.serializers import CategorySerializer, ShopSerializer, ProductInfoSerializer, OrderItemSerializer, OrderSerializer, ContactSerializer
from yaml import load as load_yaml, Loader
import requests
from backend.utils import string_to_bool
from backend.signals import new_order
from celery.result import AsyncResult
from backend.tasks import do_import, send_email


class RegisterAccount(APIView):
    """
    Класс для регистрации пользователя
    """
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
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                for p_error in password_error:
                    error_array.append(p_error)
                return JsonResponse({'Status': False, 'Errors': error_array})
            else:
                #проверка уникальности имени пользователя
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    # создаём пользователя
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ConfirmAccount(APIView):
    """
    Класс для подтверждения аккаунта
    """
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
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'], key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан email или token'})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
    

class AccountDetails(APIView):
    """
    Класс для получения и обновления данных аккаунта пользователя
    """
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

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
        # Проверка наличия обязательных полей
        if 'password' in request.data:
            # Проверка пароля на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                for p_error in password_error:
                    error_array.append(p_error)
                return JsonResponse({'Status': False, 'Errors': error_array})
            else:
                request.user.set_password(request.data['password'])
        
        # Проверка наличия остальных обязательных полей
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})
        

class LoginAccount(APIView):
    """
    Класс для авторизации пользователя
    """
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
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})
            return JsonResponse({'Status': False, 'Errors': 'Неправильно указан email или пароль'})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
        

class CategoryView(ListAPIView):
    """
    Класс для получения списка категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Класс для получения списка магазинов
    """
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


class ProductInfoView(APIView):
    """
    Класс для получения информации о продукте
    """
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
        

class BasketView(APIView):
    """
    Класс для работы с корзиной
    """
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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
        basket = Order.objects.filter(
            user_id=request.user.id, status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        
        # Сериализуем данные
        serializer = OrderItemSerializer(basket, many=True)
        return Response(serializer.data)
    
    def post(self, request: Request, *args, **kwargs):
        """
        Добавление товара в корзину
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
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
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(quantity=order_item['quantity'])
                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerUpdate(APIView):
    """
    Класс для обновления информации о партнере
    """

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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        
        url = request.data.get('url')
        if url:
            task = do_import.delay(url)
            return JsonResponse({'Status': True, 'Task': str(task), 'Task ID': task.id})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
    

class PartnerState(APIView):
    """
    Класс для управления статусом партнера
    """

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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        
        shop = request.user.shop
        if not shop:
            return JsonResponse({'Status': False, 'Error': 'Магазин не найден'}, status=404)
        else:
            serializer = ShopSerializer(shop)
            return Response(serializer.data)
        
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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=string_to_bool(state))
                return JsonResponse({'Status': True})
            except ValueError as e:
                return JsonResponse({'Status': False, 'Errors': str(e)})
        
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
    

class PartnerOrders(APIView):
    """
    Класс для получения заказов партнера
    """

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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        
        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        
        # Сериализуем данные
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
    Класс для работы с контактами
    """

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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        contact = Contact.objects.filter(user_id=request.user.id).all()
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)
    
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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
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
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
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
            

class OrderView(APIView):
    """
    Класс для работы с заказами
    """

    def get(self, request: Request, *args, **kwargs):
        """
        Получение заказов пользователя
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        order = Order.objects.filter(
            user_id=request.user.id).exclude(status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)
    
    def post(self, request: Request, *args, **kwargs):
        """
        Размещение заказа из корзины
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
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

