from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from backend.models import User, Shop, Product, ProductInfo, Category, Order, OrderItem, Contact, ConfirmEmailToken, \
    Parameter, ProductParameter


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = User
    fieldsets = (
        (None, {'fields': ('email', 'password', 'user_type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions', 'groups')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'user_type', 'is_active' )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'user_type')
    search_fields = ('email', 'first_name', 'last_name', 'company', 'position')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
    Панель управления магазинами
    """
    list_display = ('name', 'url', 'user', 'state')
    list_filter = ('state',)
    search_fields = ('name', 'url')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Панель управления категориями
    """
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('shops',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Панель управления продуктами
    """
    list_display = ('name', 'category__name')
    search_fields = ('name', 'category__name')
    list_filter = ('category__name',)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
    Панель управления информацией о продуктах
    """
    list_display = ('model', 'product__name', 'shop__name', 'quantity', 'price', 'price_rrc')
    search_fields = ('model', 'product__name', 'shop__name', 'product__category__name')
    list_filter = ('product__category__name', 'shop__name')
    readonly_fields = ('external_id',)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
    Панель управления параметрами продуктов
    """
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """
    Панель управления параметрами продуктов
    """
    list_display = ('product_info__product__name', 'parameter__name', 'value')
    search_fields = ('product_info__product__name', 'parameter__name')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Панель управления заказами
    """
    list_display = ('user', 'status', 'date', 'contact')
    search_fields = ('user__email',)
    list_filter = ('status', 'date')
    readonly_fields = ('date',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Панель управления заказанными позициями
    """
    list_display = ('order', 'product_info__product__name', 'quantity')
    search_fields = ('order__user__email', 'product_info__product__name')
    list_filter = ('order__user__email', 'product_info__product__category__name')
    readonly_fields = ('order', 'product_info',)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Панель управления контактами
    """
    list_display = ('user', 'city', 'street', 'house', 'structure', 'buildings', 'apartment', 'phone')
    search_fields = ('user__email', 'city', 'street',)
    list_filter = ('user',)


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """
    Панель управления токенами подтверждения email
    """
    list_display = ('user', 'created_at', 'key')
    search_fields = ('user__email',)
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
