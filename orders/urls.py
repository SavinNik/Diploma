"""
URL configuration for orders project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from backend.views import SendEmailView, TaskStatusView, CustomTokenObtainPairView

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenRefreshView

schema_view = get_schema_view(
    openapi.Info(
        title="API для сервиса по автоматизации закупок",
        default_version='v1',
        description="Документация для API сервиса по автоматизации закупок:",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="nikolus55@yandex.ru"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('task/status/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
    path('api/v1/', include('backend.urls', namespace='backend')),
    path('api/v1/send-email', SendEmailView.as_view(), name='send-email'),
    path('api/v1/check-task-status/<str:task_id>', TaskStatusView.as_view(), name='check-task-status'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/v1/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
