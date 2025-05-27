import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch




@pytest.fixture(scope='session')
def django_db_setup():
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_db',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
        'ATOMIC_REQUESTS': False,
    }

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user_data():
    return {
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'test@example.com',
        'password': 'testpass123',
        'company': 'Test Company',
        'position': 'Test Position',
        'user_type': 'buyer'
    }


@pytest.fixture
def authenticated_client(api_client, user_data, create_user):
    """Фикстура возвращает аутентифицированный клиент API"""
    # Логинимся
    login_url = reverse('backend:user-login')
    response = api_client.post(
        login_url,
        {'email': user_data['email'], 'password': user_data['password']},
        format='json'
    )
    assert response.status_code == 200
    token = response.json()['Access']

    # Устанавливаем токен в заголовок
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return api_client


@pytest.fixture
def create_user(db, user_data):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Удаляем пользователя, если он уже существует
    User.objects.filter(email=user_data['email']).delete()

    # Создаем пользователя с хешированным паролем
    user = User.objects.create_user(
        email=user_data['email'],
        first_name=user_data['first_name'],
        last_name=user_data['last_name'],
        company=user_data['company'],
        position=user_data['position'],
        user_type=user_data['user_type'],
        is_active=True  # Убедимся, что пользователь активен
    )
    user.set_password(user_data['password'])
    user.save()

    # Проверяем, что пароль установлен корректно
    assert user.check_password(user_data['password'])

    return user

# Отключаем отправку электронных писем
@pytest.fixture(autouse=True)
def no_email_sending():
    with patch('backend.signals.new_user_registered_signal') as mock_send:
        yield

# Отключаем логирование Celery
import logging
logging.getLogger('celery').setLevel(logging.ERROR)

# Отключаем логирование Django
logging.disable(logging.CRITICAL)

# Отключаем логирование requests
logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)