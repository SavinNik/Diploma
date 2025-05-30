from django.urls import path
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
from backend.views import PartnerUpdate, PartnerState, PartnerOrders, RegisterAccount, ConfirmAccount, \
    AccountDetails, CategoryView, ShopView, ProductInfoView, BasketView, OrderView, ContactView, LoginView, cache_info, \
    TestThrottleView, SentryTestView

app_name = 'backend'

urlpatterns = [
    # API партнера (не кэшируем)
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),

    # Аутентификация и профиль (не кэшируем)
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('user/details', AccountDetails.as_view(), name='user-details'),
    path('user/contact', ContactView.as_view(), name='user-contact'),
    path('user/login', LoginView.as_view(), name='user-login'),
    path('user/password_reset', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),

    # Кэшируемые GET-запросы
    path('categories', CategoryView.as_view(), name='categories'),
    path('shops', ShopView.as_view(), name='shops'),
    path('products', ProductInfoView.as_view(), name='products'),

    # Корзина и заказы (не кэшируем)
    path('basket', BasketView.as_view(), name='basket'),
    path('order', OrderView.as_view(), name='order'),

    # Эндпоинт для отладки кэша
    path('cache-info/', cache_info, name='cache-info'),

    # Эндпоинт для тестирования лимитов
    path('test-throttle/', TestThrottleView.as_view(), name='test_throttle'),

    # Эндпоинт для тестирования Sentry
    path('sentry-test/', SentryTestView.as_view(), name='sentry-test'),
]