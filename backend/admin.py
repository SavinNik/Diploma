from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from backend.models import User, Shop, Product, ProductInfo, Category, Order, OrderItem, Contact, ConfirmEmailToken, \
    Parameter, ProductParameter


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Административная панель для управления пользователями.
    
    Attributes:
        model: Модель пользователя
        fieldsets: Группы полей для отображения в форме редактирования
        list_display: Поля для отображения в списке пользователей
        list_filter: Поля для фильтрации списка пользователей
        search_fields: Поля для поиска пользователей
    """
    model = User
    fieldsets = (
        (None, {'fields': ('email', 'password', 'user_type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions', 'groups')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'user_type', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'user_type')
    search_fields = ('email', 'first_name', 'last_name', 'company', 'position')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
    Административная панель для управления магазинами.
    
    Attributes:
        list_display: Поля для отображения в списке магазинов
        list_filter: Поля для фильтрации списка магазинов
        search_fields: Поля для поиска магазинов
    """
    list_display = ('name', 'url', 'user', 'state')
    list_filter = ('state',)
    search_fields = ('name', 'url')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Административная панель для управления категориями.
    
    Attributes:
        list_display: Поля для отображения в списке категорий
        search_fields: Поля для поиска категорий
        filter_horizontal: Поля для горизонтального фильтра
    """
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('shops',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Административная панель для управления продуктами.
    
    Attributes:
        list_display: Поля для отображения в списке продуктов
        search_fields: Поля для поиска продуктов
        list_filter: Поля для фильтрации списка продуктов
    """
    list_display = ('name', 'category__name')
    search_fields = ('name', 'category__name')
    list_filter = ('category__name',)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
    Административная панель для управления информацией о продуктах.
    
    Attributes:
        list_display: Поля для отображения в списке информации о продуктах
        search_fields: Поля для поиска информации о продуктах
        list_filter: Поля для фильтрации списка информации о продуктах
        readonly_fields: Поля, доступные только для чтения
    """
    list_display = ('model', 'product__name', 'shop__name', 'quantity', 'price', 'price_rrc')
    search_fields = ('model', 'product__name', 'shop__name', 'product__category__name')
    list_filter = ('product__category__name', 'shop__name')
    readonly_fields = ('external_id',)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
    Административная панель для управления параметрами продуктов.
    
    Attributes:
        list_display: Поля для отображения в списке параметров
        search_fields: Поля для поиска параметров
    """
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """
    Административная панель для управления параметрами продуктов.
    
    Attributes:
        list_display: Поля для отображения в списке параметров продуктов
        search_fields: Поля для поиска параметров продуктов
    """
    list_display = ('product_info__product__name', 'parameter__name', 'value')
    search_fields = ('product_info__product__name', 'parameter__name')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Административная панель для управления заказами.
    
    Attributes:
        list_display: Поля для отображения в списке заказов
        search_fields: Поля для поиска заказов
        list_filter: Поля для фильтрации списка заказов
        readonly_fields: Поля, доступные только для чтения
    """
    list_display = ('user', 'status', 'date', 'contact')
    search_fields = ('user__email',)
    list_filter = ('status', 'date')
    readonly_fields = ('date',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Административная панель для управления заказанными позициями.
    
    Attributes:
        list_display: Поля для отображения в списке позиций заказа
        search_fields: Поля для поиска позиций заказа
        list_filter: Поля для фильтрации списка позиций заказа
        readonly_fields: Поля, доступные только для чтения
    """
    list_display = ('order', 'product_info__product__name', 'quantity')
    search_fields = ('order__user__email', 'product_info__product__name')
    list_filter = ('order__user__email', 'product_info__product__category__name')
    readonly_fields = ('order', 'product_info')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Административная панель для управления контактами пользователей.
    
    Attributes:
        list_display: Поля для отображения в списке контактов
        search_fields: Поля для поиска контактов
        list_filter: Поля для фильтрации списка контактов
    """
    list_display = ('user', 'city', 'street', 'house', 'structure', 'buildings', 'apartment', 'phone')
    search_fields = ('user__email', 'city', 'street')
    list_filter = ('user',)


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """
    Административная панель для управления токенами подтверждения email.
    
    Attributes:
        list_display: Поля для отображения в списке токенов
        search_fields: Поля для поиска токенов
    """
    def user_email(self, obj):
        return obj.user.email if obj.user else '-'
    user_email.short_description = 'Email пользователя'

    def token_created(self, obj):
        return obj.created_at
    token_created.short_description = 'Дата создания'

    def token_key(self, obj):
        return obj.key
    token_key.short_description = 'Токен'

    list_display = ('user_email', 'token_created', 'token_key')
    search_fields = ('user__email',)
