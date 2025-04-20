from django.apps import AppConfig


class BackendConfig(AppConfig):
    """
    Конфигурация приложения backend.
    
    Attributes:
        default_auto_field (str): Тип поля для автоматически создаваемых первичных ключей
        name (str): Имя приложения, используемое Django для его идентификации
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        """
        Метод для выполнения действий при запуске приложения
        """
        import backend.signals
