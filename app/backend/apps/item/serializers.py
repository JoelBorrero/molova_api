from .models import Product
from ..utils.serializers import CustomSerializer


class ProductSerializer(CustomSerializer):
    class Meta:
        model = Product
        exclude = []
