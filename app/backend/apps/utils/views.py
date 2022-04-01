import ast

from rest_framework import permissions
from rest_framework.decorators import permission_classes
from django.http import HttpResponse
from django.template import loader

from ..crawler.models import Debug, Process
from ..crawler.services import get_last_process, get_process_info, get_next_process
from ..item.models import Product
from ..item.serializers import ProductSerializer
from ..user.models import Brand
from ..user.serializers import BrandSerializer
from .constants import PROCESS_STATUS


@permission_classes([permissions.IsAdminUser])
def brand(request):
    """
    This view simulates the brands admin dashboard.
    """
    if request.user.is_superuser:
        brands = Brand.objects.all()
        serializer = BrandSerializer(brands, many=True).data
        for brand in serializer:
            percentage = Process.objects.filter(name=f'{brand["name"]} visibility').first()
            if percentage:
                brand['percentage'] = percentage.logs
        template = loader.get_template('brand.html')
        document = template.render({'brands': serializer, 'is_superuser': True})
    else:
        brand = Brand.objects.filter(id=request.user.id).first()
        serializer = BrandSerializer(brand)
        template = loader.get_template('brand.html')
        document = template.render({'brands': [serializer.data]})
    return HttpResponse(document, status=200)


@permission_classes([permissions.IsAdminUser])
def crawl(request):
    """
    This view allows admin to control scraps processes.
    """
    template = loader.get_template('crawl.html')
    bershka = Process.objects.filter(name='Bershka').first()
    blunua = Process.objects.filter(name='Blunua').first()
    mango = Process.objects.filter(name='Mango').first()
    mercedes = Process.objects.filter(name='Mercedes Campuzano').first()
    pull = Process.objects.filter(name='Pull & Bear').first()
    solua = Process.objects.filter(name='Solúa').first()
    stradivarius = Process.objects.filter(name='Stradivarius').first()
    zara = Process.objects.filter(name='Zara').first()
    data = {}
    for brand in ['bershka', 'blunua', 'mango', 'mercedes', 'pull', 'solua', 'stradivarius', 'zara']:
        try:
            exec(f'data[brand] = {{"started":{brand}.started, "updated": {brand}.updated, "status": {brand}.status}}')
            for p in PROCESS_STATUS:
                if p[0] == data[brand]['status']:
                    data[brand]['status'] = p[1]
                    break
            data[brand]['info'] = get_process_info(brand)
        except AttributeError:
            pass
    data['next'] = get_next_process()
    data['last'] = get_last_process()
    document = template.render(data)
    return HttpResponse(document, status=200)


@permission_classes([permissions.IsAdminUser])
def login(request):
    """
    This view allows user to login. Don't need authentication to see it
    """
    template = loader.get_template('auth.html')
    document = template.render({})
    return HttpResponse(document, status=200)


def product_list(request):
    """
    This view shows all products.
    """
    template = loader.get_template('items.html')
    if request.user.is_superuser:
        brand = request.GET.get('q')
    else:
        brand = Brand.objects.filter(id=request.user.id).first()
    # Pagination
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 27))
    products = Product.objects.filter(brand=brand)
    total = len(products)
    pages = total // page_size + 1
    floor_range = max(1, page - 5)
    ceil_range = min(floor_range + 9, pages)
    pages = range(floor_range, ceil_range + 1)
    url = f'?q={brand}&page='

    products = products[(page - 1) * page_size:page * page_size]
    products = ProductSerializer(products, many=True).data
    for product in products:
        try:
            product['images'] = ast.literal_eval(product['images'])
        except:
            product['images'] = 'https://' + str(products)
        if not type(product['images'][0]) is str:
            product['images'] = product['images'][0]
    brand_names = []
    for product in Product.objects.all():
        if product.brand not in brand_names:
            brand_names.append(product.brand)
    document = template.render({'brand_names': brand_names, 'count': total, 'is_superuser': request.user.is_superuser,
                                'page': page, 'pages': pages, 'page_size': page_size, 'products': products, 'url': url})
    return HttpResponse(document, status=200)


def stats(request):
    """
    This view allows admin to control scraps processes.
    """
    template = loader.get_template('stats.html')
    statistics = Debug.objects.filter(name='Statistics').first()
    if statistics:
        data = ast.literal_eval(statistics.text.replace(' ', ''))
        updated = statistics.updated
    else:
        data = None
        updated = 'Nunca'
    # keys = data.keys()
    # for key in keys:
    #     data[key.replace(' ', '')] = data.pop(key)
    # categories = [str(key).replace(' ', '') for key in data['Mango']['col'].keys()]
    document = template.render({'data': data, 'updated': updated})
    return HttpResponse(document, status=200)
