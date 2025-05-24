from functools import wraps
from django.core.cache import cache
from django.utils.encoding import force_bytes
import hashlib
from rest_framework.response import Response
import requests
from django.http import JsonResponse
from django_rest_passwordreset.models import ResetPasswordToken


class AccessMixin:
    """
    Миксин для проверки доступа к магазину
    """
    @staticmethod
    def check_shop_access(request):
        if request.user.user_type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        return None


def string_to_bool(value: str) -> bool:
    """
    Преобразует строку в логическое значение (True или False).

    Функция чувствительна к следующим значениям:
      - Истина: 'true', '1', 'yes', 'on', 'y' (регистр не важен)
      - Ложь: 'false', '0', 'no', 'off', 'n' (регистр не важен)

    Args:
        value (str): Входное значение, которое будет преобразовано в bool.

    Returns:
        bool: True — если значение соответствует истине, False — если лжи.

    Raises:
        ValueError: Если входное значение не может быть интерпретировано как логическое значение.
        TypeError: Если передан аргумент не типа str или bool.

        ValueError: Недопустимое логическое значение: 'maybe'
    """
    if isinstance(value, bool):
        return value

    if not isinstance(value, str):
        raise TypeError(f"Ожидается тип str или bool, получен {type(value)}")

    value = value.strip().lower()

    if value in ('true', '1', 'yes', 'on', 'y'):
        return True
    elif value in ('false', '0', 'no', 'off', 'n'):
        return False
    else:
        raise ValueError(f"Недопустимое логическое значение: '{value}'")

def get_password_reset_token(user):
    """
    Получает ключ сброса пароля пользователя
    """
    token_obj = ResetPasswordToken.objects.filter(user=user).order_by('-created_at').first()
    return token_obj.key if token_obj else None

def validate_url(url):
    try:
        response = requests.head(url, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        raise ValueError("Неверный URL")


def cache_api_response(timeout=60 * 15):
    """
    Декоратор для кэширования ответов API.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            # Генерируем ключ кэша на основе URL и параметров запроса
            path = request.get_full_path()
            cache_key = f'api:{request.method}:{path}'

            # Добавляем параметры запроса в ключ
            if request.GET:
                cache_key += f'?{request.META["QUERY_STRING"]}'

            cache_key = hashlib.md5(force_bytes(cache_key)).hexdigest()

            # Пытаемся получить данные из кэша
            if request.method == 'GET':
                cached_response = cache.get(cache_key)
                if cached_response is not None:
                    return Response(cached_response)

            # Если данных в кэше нет, выполняем view-функцию
            response = view_func(self, request, *args, **kwargs)

            # Кэшируем только успешные GET-запросы
            if request.method == 'GET' and response.status_code == 200:
                cache.set(cache_key, response.data, timeout)

            return response

        return _wrapped_view

    return decorator