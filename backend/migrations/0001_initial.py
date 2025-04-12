# Generated by Django 5.2 on 2025-04-12 15:20

import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Название категории')),
            ],
            options={
                'verbose_name': 'Категория',
                'verbose_name_plural': 'Список категорий',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='Parameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Название параметра')),
            ],
            options={
                'verbose_name': 'Параметр',
                'verbose_name_plural': 'Список параметров',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('company', models.CharField(blank=True, max_length=50, verbose_name='Название компании')),
                ('position', models.CharField(blank=True, max_length=50, verbose_name='Должность')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('is_active', models.BooleanField(default=False, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('user_type', models.CharField(choices=[('shop', 'Магазин'), ('buyer', 'Покупатель')], default='buyer', max_length=10, verbose_name='Тип пользователя')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ConfirmEmailToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Время создания токена')),
                ('key', models.CharField(db_index=True, max_length=64, unique=True, verbose_name='Ключ')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='confirm_email_tokens', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь связанный с токеном')),
            ],
            options={
                'verbose_name': 'Токен подтверждения email',
                'verbose_name_plural': 'Список токенов подтверждения email',
            },
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.CharField(max_length=50, verbose_name='Город')),
                ('street', models.CharField(max_length=50, verbose_name='Улица')),
                ('house', models.CharField(max_length=50, verbose_name='Дом')),
                ('structure', models.CharField(max_length=50, verbose_name='Корпус')),
                ('buildings', models.CharField(max_length=50, verbose_name='Строение')),
                ('apartment', models.CharField(max_length=50, verbose_name='Квартира')),
                ('phone', models.CharField(max_length=50, verbose_name='Телефон')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Контакты пользователя',
                'verbose_name_plural': 'Список контактов пользователя',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name='Дата заказа')),
                ('status', models.CharField(choices=[('new', 'Новый'), ('confirmed', 'Подтвержден'), ('delivered', 'Доставлен'), ('cancelled', 'Отменен'), ('sent', 'Отправлен'), ('assembled', 'Собран'), ('basket', 'Статус корзины ')], max_length=50, verbose_name='Статус заказа')),
                ('contact', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='backend.contact', verbose_name='Контакты')),
                ('user', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='orders', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Название продукта')),
                ('category', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='backend.category', verbose_name='Категория')),
            ],
            options={
                'verbose_name': 'Продукт',
                'verbose_name_plural': 'Список продуктов',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='Shop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Название магазина')),
                ('url', models.URLField(blank=True, null=True, verbose_name='Ссылка на магазин')),
                ('state', models.BooleanField(default=False, verbose_name='Статус получения заказов')),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Магазин',
                'verbose_name_plural': 'Список магазинов',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='ProductInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model', models.CharField(blank=True, max_length=50, verbose_name='Модель')),
                ('external_id', models.PositiveIntegerField(unique=True, verbose_name='Внешний идентификатор')),
                ('quantity', models.PositiveIntegerField(verbose_name='Количество')),
                ('price', models.PositiveIntegerField(verbose_name='Цена')),
                ('price_rrc', models.PositiveIntegerField(verbose_name='Рекомендуемая розничная цена')),
                ('product', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='product_infos', to='backend.product', verbose_name='Продукт')),
                ('shop', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='product_infos', to='backend.shop', verbose_name='Магазин')),
            ],
            options={
                'verbose_name': 'Информация о продукте',
                'verbose_name_plural': 'Список информации о продуктах',
            },
        ),
        migrations.AddField(
            model_name='category',
            name='shops',
            field=models.ManyToManyField(blank=True, related_name='categories', to='backend.shop', verbose_name='Магазины'),
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(verbose_name='Количество')),
                ('order', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='backend.order', verbose_name='Заказ')),
                ('product_info', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='backend.productinfo', verbose_name='Информация о продукте')),
            ],
            options={
                'verbose_name': 'Заказанная позиция',
                'verbose_name_plural': 'Список заказанных позиций',
                'constraints': [models.UniqueConstraint(fields=('order', 'product_info'), name='unique_order_item')],
            },
        ),
        migrations.CreateModel(
            name='ProductParameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=50, verbose_name='Значение')),
                ('parameter', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='product_parameters', to='backend.parameter', verbose_name='Параметр')),
                ('product_info', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='product_parameters', to='backend.productinfo', verbose_name='Информация о продукте')),
            ],
            options={
                'verbose_name': 'Параметр продукта',
                'verbose_name_plural': 'Список параметров продуктов',
                'constraints': [models.UniqueConstraint(fields=('product_info', 'parameter'), name='unique_product_parameter')],
            },
        ),
        migrations.AddConstraint(
            model_name='productinfo',
            constraint=models.UniqueConstraint(fields=('product', 'shop', 'external_id'), name='unique_product_info'),
        ),
    ]
