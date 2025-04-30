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
    Конвертирует строку в bool
    
    Args:
        value: str
        
    Returns:
        bool: True for 'true', '1', 'yes', 'on', 'y'
              False for 'false', '0', 'no', 'off', 'n'
              
    Raises:
        ValueError: If the value cannot be converted to boolean
    """
    if isinstance(value, bool):
        return value
    if value.lower() in ('true', '1', 'yes', 'on', 'y'):
        return True
    elif value.lower() in ('false', '0', 'no', 'off', 'n'):
        return False
    raise ValueError(f"Invalid boolean value: {value}")

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