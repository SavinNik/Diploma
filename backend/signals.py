from typing import Type
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import User, Order
from backend.tasks import send_email
import logging

logger = logging.getLogger(__name__)

# Сигналы для новых пользователей и новых заказов
new_user_registered = Signal()
new_order = Signal()


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
        try:
            # Создаем токен для подтверждения email
            token = default_token_generator.make_token(instance)
            # Отправляем письмо с токеном для подтверждения email
            send_email.delay(
                # Заголовок письма
                subject='Подтверждение email',
                # Текст письма
                message=f'Ваш токен: {token}',
                # Отправитель
                from_email=settings.EMAIL_HOST_USER,
                # Получатели
                recipient_list=[instance.email]
            )
        except Exception as e:
            logger.error(f'При отправке письма произошла ошибка: {e}')


@receiver(new_order)
def new_order_signal(user_id: int, *args, **kwargs):
    """
    Сигнал для отправки письма при размещении нового заказа

    Args:
        user_id: ID пользователя
        *args: Дополнительные аргументы
        **kwargs: Дополнительные аргументы
    """
    try:
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
    except Exception as e:
        logger.error(f'При отправке письма произошла ошибка: {e}')


@receiver(reset_password_token_created)
def password_reset_token_created(sender: Type[User], instance: User, reset_password_token, *args, **kwargs):
    """
    Отправляем письмо с токеном для сброса пароля
    :param sender: Класс, который вызвал сигнал
    :param instance: Экземпляр класса, который вызвал сигнал
    :param reset_password_token: Токен для сброса пароля
    :param args: Дополнительные аргументы
    :param kwargs: Дополнительные аргументы
    """
    try:
        send_email.delay(
            # Заголовок письма
            subject='Сброс пароля',
            # Текст письма
            message=f'Токен для сброса пароля: {reset_password_token.key}',
            # Отправитель
            from_email=settings.EMAIL_HOST_USER,
            # Получатели
            recipient_list=[reset_password_token.user.email]
        )
    except Exception as e:
        logger.error(f'При отправке письма произошла ошибка: {e}')
