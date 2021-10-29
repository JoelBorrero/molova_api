from .models import Process
from backend.apps.utils.serializers import CustomSerializer


class ProcessSerializer(CustomSerializer):
    class Meta:
        model = Process
        exclude = []
