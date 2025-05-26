import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

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