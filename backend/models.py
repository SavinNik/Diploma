from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from django.db import models



# Константы для состояния заказа
STATES_CHOICES = (
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('delivered', 'Доставлен'),
    ('cancelled', 'Отменен'),
    ('sent', 'Отправлен'),
    ('assembled', 'Собран'),
    ('basket', 'Статус корзины '),
)

# Константы для типа пользователя
USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)


class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями
    """
    user_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Создает и сохраняет пользователя с указанными email и паролем.

        Args:
            email (str): Электронная почта пользователя.
            password (str): Пароль пользователя.
            **extra_fields (dict): Дополнительные поля пользователя.

        Returns:
            User: Созданный пользователь.

        Raises:
            ValueError: Если email не указан.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        Создает обычного пользователя.

        Args:
            email (str): Электронная почта пользователя.
            password (str): Пароль пользователя.
            **extra_fields: Дополнительные поля пользователя.

        Returns:
            User: Созданный пользователь.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """
        Создает суперпользователя.

        Args:
            email (str): Электронная почта суперпользователя.
            password (str): Пароль суперпользователя.
            **extra_fields: Дополнительные поля суперпользователя.

        Returns:
            User: Созданный суперпользователь.

        Raises:
            ValueError: Если is_staff или is_superuser не установлены в True.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Стандартная модель пользователя
    """
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'

    email = models.EmailField(_('email address'), unique=True)
    company = models.CharField(verbose_name='Название компании', max_length=50, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=50, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    is_active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    user_type = models.CharField(verbose_name='Тип пользователя', max_length=10, choices=USER_TYPE_CHOICES, default='buyer')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Mete:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Список пользователей'
        ordering = ('email',)


class Shop(models.Model):
    """
    Модель магазина
    """
    objects = models.manager.Manager()
    name = models.CharField(verbose_name='Название магазина', max_length=50)
    url = models.URLField(verbose_name='Ссылка на магазин', null=True, blank=True)
    user = models.OneToOneField(User, verbose_name='Пользователь', on_delete=models.CASCADE, null=True, blank=True)
    state = models.BooleanField(verbose_name='Статус получения заказов', default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Список магазинов'
        ordering = ('-name',)



























