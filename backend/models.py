from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from django.db import models
from django_rest_passwordreset.tokens import get_token_generator

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
    user_type = models.CharField(verbose_name='Тип пользователя', max_length=10, choices=USER_TYPE_CHOICES,
                                 default='buyer')

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


class Category(models.Model):
    """
    Модель категории
    """
    objects = models.manager.Manager()
    name = models.CharField(verbose_name='Название категории', max_length=50)
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Список категорий'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Модель продукта
    """
    objects = models.manager.Manager()
    name = models.CharField(verbose_name='Название продукта', max_length=50)
    category = models.ForeignKey(Category, verbose_name='Категория', related_name='products', on_delete=models.CASCADE,
                                 blank=True)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Список продуктов'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """
    Модель информации о продукте
    """
    objects = models.manager.Manager()
    model = models.CharField(verbose_name='Модель', max_length=50, blank=True)
    external_id = models.PositiveIntegerField(verbose_name='Внешний идентификатор', unique=True)
    product = models.ForeignKey(Product, verbose_name='Продукт', related_name='product_infos', on_delete=models.CASCADE,
                                blank=True)
    shop = models.ForeignKey(Shop, verbose_name='Магазин', related_name='product_infos', on_delete=models.CASCADE,
                             blank=True)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.PositiveIntegerField(verbose_name='Цена')
    price_rrc = models.PositiveIntegerField(verbose_name='Рекомендуемая розничная цена')

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = 'Список информации о продуктах'
        constraints = [
            models.UniqueConstraint(fields=['product', 'shop', 'external_id'], name='unique_product_info')
        ]


class Parameter(models.Model):
    """
    Модель параметра продукта
    """
    objects = models.manager.Manager()
    name = models.CharField(verbose_name='Название параметра', max_length=50)

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Список параметров'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """
    Модель параметра продукта
    """
    objects = models.manager.Manager()
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                     related_name='product_parameters', on_delete=models.CASCADE, blank=True)
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр', related_name='product_parameters',
                                  on_delete=models.CASCADE, blank=True)
    value = models.CharField(verbose_name='Значение', max_length=50)

    class Meta:
        verbose_name = 'Параметр продукта'
        verbose_name_plural = 'Список параметров продуктов'
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter')
        ]


class Contact(models.Model):
    """
    Модель контактов пользователя
    """
    objects = models.manager.Manager()
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='contacts', on_delete=models.CASCADE)
    city = models.CharField(verbose_name='Город', max_length=50)
    street = models.CharField(verbose_name='Улица', max_length=50)
    house = models.CharField(verbose_name='Дом', max_length=50)
    structure = models.CharField(verbose_name='Корпус', max_length=50)
    buildings = models.CharField(verbose_name='Строение', max_length=50)
    apartment = models.CharField(verbose_name='Квартира', max_length=50)
    phone = models.CharField(verbose_name='Телефон', max_length=50)

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = 'Список контактов пользователя'

    def __str__(self):
        return f'{self.city} {self.street} {self.house}'


class Order(models.Model):
    """
    Модель заказа
    """
    objects = models.manager.Manager()
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='orders', on_delete=models.CASCADE,
                             blank=True)
    date = models.DateTimeField(verbose_name='Дата заказа', auto_now_add=True)
    status = models.CharField(verbose_name='Статус заказа', max_length=50, choices=STATES_CHOICES)
    contact = models.ForeignKey(Contact, verbose_name='Контакты', null=True, on_delete=models.CASCADE, blank=True)

    class Mete:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Список заказов'
        ordering = ('-date',)

    def __str__(self):
        return str(self.date)


class OrderItem(models.Model):
    """
    Модель элемента заказа
    """
    objects = models.manager.Manager()
    order = models.ForeignKey(Order, verbose_name='Заказ', related_name='order_items', on_delete=models.CASCADE,
                              blank=True)
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                     related_name='order_items', on_delete=models.CASCADE, blank=True)
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Заказанная позиция'
        verbose_name_plural = 'Список заказанных позиций'
        constraints = [
            models.UniqueConstraint(fields=['order', 'product_info'], name='unique_order_item')
        ]


class ConfirmEmailToken(models.Model):
    """
    Модель токена подтверждения email
    """
    objects = models.manager.Manager()

    @staticmethod
    def generate_key():
        """
        Генерирует случайный ключ с помощью os.urandom и binascii.hexlify

        :return:
            str: Сгенерированный ключ
        """
        return get_token_generator().generate_token()

    user = models.ForeignKey(User, related_name='confirm_email_tokens', on_delete=models.CASCADE, verbose_name=_('Пользователь связанный с токеном'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Время создания токена'))
    key = models.CharField(_('Ключ'), max_length=64, db_index=True, unique=True)

    def seve(self, *args, **kwargs):
        """
        Сохраняет токен, генерируя новый ключ, если его не было

        Args:
            *args: Позиционные аргументы
            **kwargs: Ключевые аргументы

        Returns:
             ConfirmEmailToken: Сохраненный токен
        """
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Токен подтверждения email'
        verbose_name_plural = 'Список токенов подтверждения email'

    def __str__(self):
        return f'Токен сброса пароля для {self.user}'
