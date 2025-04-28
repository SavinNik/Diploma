from django.http import JsonResponse


class AccessMixin:
    """
    Миксин для проверки доступа к магазину
    """
    @staticmethod
    def check_shop_access(request):
        if request.user.user_type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        return None

    @staticmethod
    def check_auth(request):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
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
