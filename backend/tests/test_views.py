import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test.utils import override_settings
from rest_framework.test import APIClient
from django.core.cache import cache

# Тестирование регистрации пользователя
@pytest.mark.django_db
def test_register_user(api_client, user_data):
    url = reverse('backend:user-register')

    # Отправляем запрос
    response = api_client.post(url, user_data, format='json')

    # Проверяем статус код
    assert response.status_code == 200

    try:
        response_data = response.json()

        # Проверяем, что в ответе есть ожидаемые поля
        assert 'Status' in response_data
        assert response_data.get('Status') is True

    except json.JSONDecodeError as e:
        pytest.fail(f"Response is not valid JSON: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error: {e}")

# Тестирование входа пользователя
@pytest.mark.django_db
def test_login_user(api_client, user_data, create_user):
    User = get_user_model()
    # Проверяем, что пользователь создан
    user = User.objects.get(email=user_data['email'])

    # Пробуем аутентифицироваться напрямую
    from django.contrib.auth import authenticate
    authenticated_user = authenticate(
        email=user_data['email'],
        password=user_data['password']
    )

    url = reverse('backend:user-login')
    login_user_data = {
        'email': user_data['email'],
        'password': user_data['password']
    }

    # Отправляем запрос
    response = api_client.post(url, login_user_data, format='json')

    # Проверяем статус код
    assert response.status_code == 200

    try:
        response_data = response.json()
        assert 'Status' in response_data
        assert response_data['Status'] is True
        assert 'Access' in response_data
        assert 'Refresh' in response_data

    except json.JSONDecodeError:
        pytest.fail(f"Ответ не является валидным JSON: {response.content}")
    except Exception as e:
        pytest.fail(f"Произошла ошибка: {e}")

# Тестирование обновления данных пользователя
@pytest.mark.django_db
def test_update_user(authenticated_client):

    url = reverse('backend:user-details')
    update_user_data = {
        'first_name': 'Updated',
        'last_name': 'User',
        'company': 'Updated Company',
        'position': 'Updated Position',
    }

    # Отправляем запрос
    response = authenticated_client.post(url, update_user_data, format='json')

    # Проверяем статус код
    assert response.status_code == 200

    try:
        response_data = response.json()
        assert 'Status' in response_data
        assert response_data['Status'] is True

    except json.JSONDecodeError:
        pytest.fail(f"Ответ не является валидным JSON: {response.content}")
    except Exception as e:
        pytest.fail(f"Произошла ошибка: {e}")

# Тестирование получения списка категорий
@pytest.mark.django_db
def test_get_categories(authenticated_client):
    url = reverse('backend:categories')

    # Отправляем запрос
    response = authenticated_client.get(url)

    # Проверяем статус код и содержимое
    assert response.status_code == 200
    categories = response.json()
    assert isinstance(categories, list)

    # Если есть категории, проверяем их структуру
    if categories:
        category = categories[0]
        assert 'id' in category
        assert 'name' in category

# Тестирование получения списка магазинов
@pytest.mark.django_db
def test_get_shops(authenticated_client):
    url = reverse('backend:shops')

    # Отправляем запрос
    response = authenticated_client.get(url)

    # Проверяем статус код и содержимое
    assert response.status_code == 200
    shops = response.json()
    assert isinstance(shops, list)

    # Если есть магазины, проверяем их структуру
    if shops:
        shop = shops[0]
        assert 'id' in shop
        assert 'name' in shop

# Тестирование получения списка товаров
@pytest.mark.django_db
def test_get_products(authenticated_client):
    url = reverse('backend:products')

    # Отправляем запрос
    response = authenticated_client.get(url)

    # Проверяем статус код и содержимое
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)

    # Если есть товары, проверяем их структуру
    if products:
        product = products[0]
        assert 'id' in product
        assert 'model' in product
        assert 'price' in product
        assert 'price_rrc' in product
        assert 'quantity' in product

@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache'
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [
            'rest_framework.throttling.AnonRateThrottle',
            'rest_framework.throttling.UserRateThrottle',
        ],
        'DEFAULT_THROTTLE_RATES': {
            'anon': '3/day',
            'user': '5/day',
        }
    }
)
@pytest.mark.django_db
def test_throttling(create_user):
    client = APIClient()
    url = '/api/test-throttle/'

    # Анонимный пользователь
    for i in range(4):
        response = client.get(url)
        assert response.status_code == 200 if i < 3 else 429

    # Авторизованный пользователь
    client.force_authenticate(user=create_user)

    for i in range(6):
        response = client.get(url)
        assert response.status_code == 200 if i < 5 else 429

    # Очистка кэша после теста
    cache.clear() # noqa