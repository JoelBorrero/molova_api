from .models import Product
from ..utils.serializers import CustomSerializer


class ProductSerializer(CustomSerializer):
    class Meta:
        model = Product
        exclude = []


class ProductToPostSerializer(CustomSerializer):
    class Meta:
        model = Product
        exclude = ['id', 'archived', 'created', 'updated', 'approved', 'active']
