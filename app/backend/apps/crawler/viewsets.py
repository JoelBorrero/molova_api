from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Process, Debug
from .serializers import ProcessSerializer
from .tasks import crawl_bershka, crawl_stradivarius
from ..item.models import Product
from ..item.serializers import ProductSerializer


class ProcessViewSet(viewsets.ModelViewSet):
    model = Process
    queryset = model.objects.all()
    serializer_class = ProcessSerializer

    @action(detail=False, methods=['POST'])
    def start_bershka(self, request):
        crawl_bershka.delay()
        return Response({'status': 'Bershka started'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'])
    def start_stradivarius(self, request):
        crawl_stradivarius.delay()
        return Response({'status': 'Stradivarius started'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'])
    def broken(self, request):
        items = Product.objects.filter(active=False)
        serializer = ProductSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
