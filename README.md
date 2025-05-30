# Проект: backend-приложение для автоматизации закупок

## Оглавление

1. [Описание проекта](#Описание-проекта)
2. [Функциональные возможности](#Функциональные-возможности)
3. [Технологии и инструменты](#Технологии-и-инструменты)
4. [Архитектура приложения](#Архитектура-приложения)
5. [Запуск приложения](#Запуск-приложения)
6. [API Endpoints](#API-Endpoints)
7. [Модели данных](#Модели-данных)
8. [Celery задачи](#Celery-задачи)
9. [Безопасность](#Безопасность)
10. [Тестирование](#Тестирование). 


## Описание проекта

Проект представляет собой REST API для автоматизации закупок, включающий:
- Управление магазинами и товарами
- Обработку заказов и корзины
- Отправку уведомлений
- Регистрация и аутентификация пользователей
- Интеграцию с Celery для асинхронных задач
- Документацию через Swagger/OpenAPI

## Функциональные возможности

- **Регистрация и аутентификация**: Регистрация новых пользователей с подтверждением email и аутентификация существующих.
- **Управление магазинами и товарами**: Обновление данных магазина через YAML-файл, управление статусом.
- **Продукты**: Каталог товаров с фильтрацией по категориям и магазинам.
- **Заказы**: Создание, обновление и удаление заказов.
- **Корзина**: Добавление/удаление товаров, обновление количества товаров в корзине.
- **Контакты**: Управление контактной информацией пользователя.

## Технологический стек

- **Python 3.12**
- **Django 5.2**
- **Django Rest Framework (DRF)**
- **JWT-аутентификация (rest_framework_simplejwt)**
- **PostgreSQL**
- **Redis**
- **Celery**
- **Docker**
- **Swagger/OpenAPI**
- **Pytest**
- **Sentry**

## Архитектура приложения
```
├── .dockerignore
├── Dockerfile
├── README.md
├── backend
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── models
│   │   ├── __init__.py
│   │   └── models.py
│   ├── serializers.py
│   ├── signals.py
│   ├── tasks.py
│   ├── templates
│   │   └── admin
│   │       └── run_task_form.html
│   ├── tests.py
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_views.py
│   ├── urls.py
│   ├── utils.py
│   └── views.py
├── docker-compose.yml
├── import_data
│   ├── Shop1.yaml
│   └── Shop2.yaml
├── manage.py
├── media
│   └── export_data
│       └── М.Видео_export.yaml
├── orders
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── requirements.txt
```


- **Установка зависимостей**:
```bash
pip install -r requirements.txt
```
- **Конфигурация**:
1. Создайте файл `.env` в корневой директории проекта.
2. Скопируйте содержимое `.env.example` в `.env`.
3. Замените значения переменных окружения в `.env` на свои.
4. Запустите контейнеры Docker:
```bash
docker compose build
docker compose up -d
```
5. Запустите миграции:
```bash
python manage.py migrate
```
6. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

## API Endpoints

1. **Аутентификация**
`POST /api/v1/register/`
```json
{
  "first_name": "string",
  "last_name": "string",
  "email": "string",
  "password": "string",
  "company": "string",
  "position": "string"
}
```

**Авторизация**
`POST /api/v1/login/`
```json
{
  "email": "string",
  "password": "string"
}
```

**Сброс пароля через почту**
`POST /api/v1/password-reset/`

2. **Магазины**

**Обновление данных магазина через YAML-файл**
`POST /api/v1/shop/update/`
```json
{
    "url": "https://example.com/data.yaml"
}
```

**Получение списка магазинов**
`GET /api/v1/shops/`

3. **Продукты**

**Получение товаров с фильтрацией по категориям и магазинам**
`GET /api/v1/products/`
- `category_id` - ID категории
- `shop_id` - ID магазина

4. **Заказы**

**Получение списка заказов**
`GET /api/v1/orders/`

**Создание заказа**
`POST /api/v1/orders/`
```json
{
    "id": 1,
    "contact": 1
}
```

5. **Контакты**

**Создание контакта**
`POST /api/v1/contacts/`
```json
{
    "city": "string",
    "street": "string",
    "house": "string",
    "building": "string",
    "structure": "string",
    "apartment": "string",
    "phone": "string" 
}
```

**Обновление контакта**
`PUT /api/v1/contacts/`
```json
{
    "id": 1,
    "city": "new_city"
}
```

6. **Корзина**

**Добавление товара в корзину**
`POST /api/v1/basket/`
```json
{
    "items": [
        {
            "product_info": 1,
            "quantity": 1
        }
    ]
}
```

**Удаление товара из корзины**
`DELETE /api/v1/basket/`
```json
{
    "items": "1,2,3"
}
```

**Обновление количества товаров в корзине**
`PUT /api/v1/basket/`
```json
{
    "items": [
        {
            "id": 1,
            "quantity": 2
        }
    ]
}
```

## Модели данных

- **User**: Расширенная модель пользователя с типами shop и buyer.
- **Shop**: Модель магазина, связанная с моделью User.
- **Category**: Модель категории.
- **Product**: Модель продукта, связанная с моделью Category.
- **ProductInfo**: Модель информации о продукте, связанная с моделями Shop и Product.
- **Order**: Модель заказа.
- **OrderItem**: Модель товара в заказе, связанная с моделями Order и ProductInfo.
- **Contact**: Модель контакта пользователя.
- **Parameter**: Модель параметра продукта.
- **BasketItem**: Модель товара в корзине, связанная с моделями Basket и ProductInfo.

## Celery задачи

- **send_email_task**: Отправка уведомления о заказе.
- **do_import**: Импорт данных из YAML-файла.
- **do_export**: Экспорт данных в YAML-файл.

## Админка Django

- Настройки для управления категориями, магазинами, продуктами, заказами, контактами.
- Интерфейс для запуска Celery задач.

## Безопасность

- JWT токены для аутентификации.
- Подтверждение email пользователем.
- Эндпоинты защищены, требуется передача токена в заголовке Authorization: Bearer <token>.
- Пароли хранятся в хешах.

## Тестирование

- Pytest для тестирования API.
![Coverage](https://img.shields.io/badge/Coverage-44%25-success?color=brightgreen )















