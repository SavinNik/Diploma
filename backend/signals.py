from typing import Type
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django_rest_passwordreset.signals import reset_password_token_created
from backend.models import User, Order
from backend.tasks import send_email


# Сигналы для новых пользователей и новых заказов
new_user_registered = Signal()
new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender: Type[User], instance: User, reset_password_token, *args, **kwargs):
    """
    Отправляет письмо с токеном для сброса пароля

    Args:
        sender: Модель, которая вызвала сигнал
        instance: Экземпляр модели, которая вызвала сигнал
        reset_password_token: Токен для сброса пароля
        *args: Дополнительные аргументы
        **kwargs: Дополнительные аргументы
    """
    # Отправляем письмо с токеном для сброса пароля
    message = EmailMultiAlternatives(
        # Заголовок письма
        f'Токен для сброса пароля для {reset_password_token.user}',
        # Текст письма
        reset_password_token.key,
        # Отправитель
        settings.EMAIL_HOST_USER,
        # Получатели
        [reset_password_token.user.email]
    )
    message.send()


@receiver(post_save, sender=User)
def new_user_registered_signal(sender: Type[User], instance: User, created: bool, *args, **kwargs):
    """
    Сигнал для отправки письма при регистрации нового пользователя

    Args:
        sender: Модель, которая вызвала сигнал
        instance: Экземпляр модели, которая вызвала сигнал
        created: Флаг, указывающий, был ли создан новый экземпляр
        *args: Дополнительные аргументы
        **kwargs: Дополнительные аргументы
    """
    if created:
        # Создаем токен для подтверждения email
        token, _ = ConfirmEmailToken.objects.get_or_create(user=instance)
        # Отправляем письмо с токеном для подтверждения email
        send_email.delay(
            # Заголовок письма
            f'Токен для подтверждения email для {instance.email}',
            # Текст письма
            token.key,
            # Отправитель
            settings.EMAIL_HOST_USER,
            # Получатели
            [instance.email]
        )


@receiver(new_order)
def new_order_signal(user_id: int, *args, **kwargs):
    """
    Сигнал для отправки письма при размещении нового заказа

    Args:
        user_id: ID пользователя
        *args: Дополнительные аргументы
        **kwargs: Дополнительные аргументы
    """
    # Получаем пользователя по ID
    user = User.objects.get(id=user_id)
    # Получаем заказ
    order = Order.objects.filter(user_id=user_id, status='basket').first()
    if order:
        # Обновляем статус заказа
        order.status = 'new'
        order.save()
    # Отправляем письмо пользователю о новом заказе
    send_email.delay(
        # Заголовок письма
        f'Обновление статуса заказа',
        # Текст письма
        'Заказ сформирован',
        # Отправитель
        settings.EMAIL_HOST_USER,
        # Получатели
        [user.email]
    )
