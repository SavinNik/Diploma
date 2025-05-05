from django.contrib import admin, messages
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect,render
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from backend.models import User, Shop, Product, ProductInfo, Category, Order, OrderItem, Contact, \
    Parameter, ProductParameter, TaskStatus
from tasks import do_import, do_export


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
    list_display = ('name', 'url', 'user', 'state', 'export_button')
    list_filter = ('state',)
    search_fields = ('name', 'url')

    def export_button(self, obj):
        """Отображает кнопку 'Экспортировать' для каждого магазина."""
        return format_html(
            '<a class="button" href="{}">📤 Экспортировать</a>',
            reverse('admin:run-do-export', args=[obj.id])
        )

    export_button.short_description = 'Экспорт товаров'
    export_button.allow_tags = True  # Устаревшее, но можно оставить для совместимости


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
    list_display = ('user', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone')
    search_fields = ('user__email', 'city', 'street')
    list_filter = ('user',)


@admin.register(TaskStatus)
class TaskStatusAdmin(admin.ModelAdmin):
    change_list_template = "admin/task_status.html"
    model = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def get_queryset(self, request):
        return super().get_queryset(request)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.admin_site.admin_view(self.run_do_import), name='run-do-import'),
            path('export/<int:shop_id>/', self.admin_site.admin_view(self.run_do_export), name='run-do-export'),
        ]
        return custom_urls + urls

    def run_do_import(self, request):
        if request.method == 'POST':
            url = request.POST.get('url')
            if not url:
                messages.error(request, 'URL не указан')
                return redirect('admin:run-do-import')

            task = do_import.delay(url=url)
            messages.success(request, f'Задача импорта запущена. ID задачи: {task.id}')
            return redirect('admin:run-do-import')

        return render(request, 'admin/run_task_form.html', {
            'title': 'Импорт данных магазина',
            'task_name': 'do_import',
            'form_action': 'admin:run-do-import'
        })

    def run_do_export(self, request, shop_id):
        task = do_export.delay(shop_id=shop_id)
        messages.success(request, f'Экспорт магазина запущен. ID задачи: {task.id}')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/backend/shop/'))

