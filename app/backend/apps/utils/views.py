from rest_framework import permissions
from rest_framework.decorators import permission_classes
from django.http import HttpResponse
from django.template import loader

from ..user.models import Brand
from ..user.serializers import BrandSerializer


@permission_classes([permissions.IsAdminUser])
def login(request, *args, **kwargs):
    """
    This view allows user to login. Don't need authentication to see it
    """
    template = loader.get_template('auth.html')
    document = template.render({})
    return HttpResponse(document, status=200)


@permission_classes([permissions.IsAdminUser])
def crawl(request, *args, **kwargs):
    """
    This view allows admin to control scraps processes.
    """
    template = loader.get_template('crawl.html')
    document = template.render({})
    return HttpResponse(document, status=200)


@permission_classes([permissions.IsAdminUser])
def brand(request, *args, **kwargs):
    """
    This view simulates the brands admin dashboard.
    """
    brands = Brand.objects.filter(owner=request.user)
    serializer = BrandSerializer(brands, many=True)
    template = loader.get_template('brand.html')
    document = template.render({'user': request.user, 'brands': serializer.data})
    return HttpResponse(document, status=200)
