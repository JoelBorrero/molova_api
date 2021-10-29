from django.contrib.auth.models import User

from ..user.models import Brand
from ..utils.serializers import CustomSerializer


class BrandSerializer(CustomSerializer):
    class Meta:
        model = Brand
        exclude = []


class UserSerializer(CustomSerializer):
    class Meta:
        model = User
        exclude = []
