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
