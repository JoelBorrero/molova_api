import ast

from rest_framework import permissions
from rest_framework.decorators import permission_classes
from django.http import HttpResponse
from django.template import loader

from ..crawler.models import Debug
from ..item.models import Product
from ..item.serializers import ProductSerializer
from ..user.models import Brand
from ..user.serializers import BrandSerializer


@permission_classes([permissions.IsAdminUser])
def brand(request):
    """
    This view simulates the brands admin dashboard.
    """
    if request.user.is_superuser:
        brands = Brand.objects.all()
        serializer = BrandSerializer(brands, many=True)
        template = loader.get_template('brand.html')
        document = template.render({'brands': serializer.data, 'is_superuser': True})
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
    document = template.render({})
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
        brand = Brand.objects.get(id=request.user.id)
    products = Product.objects.filter(brand=brand)
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
    document = template.render({'brand_names': brand_names, 'products': products, 'count': len(products),
                                'is_superuser': request.user.is_superuser})
    return HttpResponse(document, status=200)


def stats(request):
    """
    This view allows admin to control scraps processes.
    """
    template = loader.get_template('stats.html')
    statistics = Debug.objects.filter(name='Statistics').first()
    data = ast.literal_eval(statistics.text.replace(' ', ''))
    # keys = data.keys()
    # for key in keys:
    #     data[key.replace(' ', '')] = data.pop(key)
    # categories = [str(key).replace(' ', '') for key in data['Mango']['col'].keys()]
    document = template.render({'data': data, 'updated': statistics.updated})
    return HttpResponse(document, status=200)
