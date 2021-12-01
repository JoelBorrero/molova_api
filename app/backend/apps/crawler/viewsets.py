from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import ProcessSerializer
from .tasks import *
from ..item.models import Product
from ..item.serializers import ProductSerializer


class ProcessViewSet(viewsets.ModelViewSet):
    model = Process
    queryset = model.objects.all()
    serializer_class = ProcessSerializer

    @action(detail=False, methods=['POST'])
    def start_crawling(self, request):
        brand = request.data['brand']
        if brand == 'Bershka':
            crawl_bershka.delay()
        elif brand == 'Mango':
            crawl_mango.delay()
        elif brand == 'Pull & Bear':
            crawl_pull.delay()
        elif brand == 'Stradivarius':
            crawl_stradivarius.delay()
        elif brand == 'Solua Accesorios':
            crawl_solua.delay()
        else:
            brand += ' not found. Not'
        return Response({'status': brand + ' started'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'])
    def sync(self, request):
        # pull_from_molova()
        pull_from_molova.delay()
        return Response({'status': 'Working'}, status=status.HTTP_200_OK)
