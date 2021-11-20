from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..crawler.models import Debug
from ..item.models import Product
from ..item.serializers import ProductSerializer
from ..item.services import generate_prefix, read_from_excel, read_to_add_images
from ..user.models import Brand
from ..user.serializers import BrandSerializer, UserSerializer


class BrandViewSet(viewsets.ViewSet):
    model = Brand
    queryset = model.objects.all()
    serializer_class = BrandSerializer
    permission_classes = (AllowAny,)

    def create(self, request):
        """
        {nit: 123, name: name}
        """
        data = request.data
        brand = Brand.objects.create(username=data['nit'], password=make_password(data['nit']), first_name=data['name'],
                                     name=data['name'], nit=data['nit'], prefix=generate_prefix(data['name']))
        serializer = BrandSerializer(brand)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'])
    def massive_upload(self, request):
        """
        {excel: file}
        """
        data = request.data
        result = read_from_excel(data['excel'],  # data['photos'],
                                 request.user.id)
        return Response({'response': result}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'])
    def update_files(self, request):
        """
        Exec function to fill product images in excel files
        """
        read_to_add_images()
        return Response({'status': 'Done'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'])
    def get_my_products(self, request):
        items = Product.objects.all()
        serializer = ProductSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# class Registration(viewsets.ModelViewSet):
#     model = Brand
#     queryset = model.objects.all()
#     serializer_class = BrandSerializer
#     permission_classes = [AllowAny]
#
#     @action(detail=False, methods=['POST'])
#     def create_user(self, request):
#         data = request.data
#         user = User.objects.create_user(username=data['username'], password=data['password'],
#                                         first_name=data.get('name', ''))
#         serializer = UserSerializer(user)
#         return Response(serializer.data, status=status.HTTP_201_CREATED)
