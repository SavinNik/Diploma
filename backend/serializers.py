from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from backend.models import User, Shop, Product, ProductInfo, Category, Order, OrderItem, Contact, \
    ProductParameter


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Сериализатор токена
    """
    @classmethod
    def get_token(cls, user):
        """
        Добавляем email
        """
        token = super().get_token(user)
        token['email'] = user.email
        return token


class ContactSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели Contact
    """

    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class ContactUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone')
        extra_kwargs = {
            'city': {'required': False},
            'street': {'required': False},
            'house': {'required': False},
            'phone': {'required': False},
            'structure': {'required': False},
            'building': {'required': False},
            'apartment': {'required': False}
        }


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели User
    """
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'password', 'contacts', 'company', 'position')
        read_only_fields = ('id',)
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance


class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор модели Category
    """

    class Meta:
        model = Category
        fields = ('id', 'name',)
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели Shop
    """

    class Meta:
        model = Shop
        fields = ('id', 'name', 'state',)
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели Product
    """
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('name', 'category',)


class ProductParameterSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели ProductParameter
    """
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели ProductInfo
    """
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'model', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters')
        read_only_fields = ('id',)


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели OrderItem
    """

    class Meta:
        model = OrderItem
        fields = ('id', 'order', 'product_info', 'quantity')
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True},
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    """
    Сериализатор для создания модели OrderItem
    """
    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели Order
    """
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)
    total_sum = serializers.IntegerField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'status', 'date', 'total_sum', 'contact')
        read_only_fields = ('id',)
