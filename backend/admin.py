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
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions', 'groups')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'type', 'is_active' )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'type')
    search_fields = ('email', 'first_name', 'last_name', 'company', 'position')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
    Панель управления магазинами
    """
    model = Shop
    list_display = ('name', 'url', 'user', 'state')
    list_filter = ('state',)
    search_fields = ('name', 'url')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Панель управления категориями
    """
    model = Category
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('shops',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Панель управления продуктами
    """
    model = Product
    list_display = ('name', 'category')
    search_fields = ('name',)
    filter_horizontal = ('category',)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
    Панель управления информацией о продуктах
    """
    model = ProductInfo


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
    Панель управления параметрами продуктов
    """
    model = Parameter


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """
    Панель управления параметрами продуктов
    """
    model = ProductParameter


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Панель управления заказами
    """
    model = Order


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Панель управления заказанными позициями
    """
    model = OrderItem


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Панель управления контактами
    """
    model = Contact


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """
    Панель управления токенами подтверждения email
    """
    model = ConfirmEmailToken
