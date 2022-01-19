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
        elif brand == 'Blunua':
            crawl_blunua.delay()
        elif brand == 'Mango':
            crawl_mango.delay()
        elif brand == 'Pull & Bear':
            crawl_pull.delay()
        elif brand == 'Stradivarius':
            crawl_stradivarius.delay()
        elif brand == 'Solua Accesorios':
            crawl_solua.delay()
        elif brand == 'Zara':
            crawl_zara.delay()
        else:
            brand += ' not found. Not'
        return Response({'status': brand + ' started'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'])
    def sync(self, request):
        pull_from_molova.delay(request.data['brand'])
        return Response({'status': 'Working'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'])
    def activate_product(self, request):
        product = Product.objects.get(id=request.data['brand'])  # Should be id instead brand
        if product.active:
            delete_from_remote(product.id_producto)
            product.active = False
            res = ''
        else:
            res = post_item(product)
            product.active = True
        product.save()
        return Response({'status': f'{product.name} set visible to {product.active} ({res})'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'])
    def update_links(self, request):
        """Update links to search in crawl process"""
        update_brand_links(request.data.get('brand', ''))
        return Response({'status': brand + ' started'}, status=status.HTTP_200_OK)

