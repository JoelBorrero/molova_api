from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..crawler.models import Debug
from ..item.services import read_from_excel, generate_prefix
from ..user.models import Brand
from ..user.serializers import BrandSerializer, UserSerializer


class BrandViewSet(viewsets.ModelViewSet):
    model = Brand
    queryset = model.objects.all()
    serializer_class = BrandSerializer

    def create(self, request):
        data = request.data
        if Brand.objects.filter(Q(name=data['name']) | Q(nit=data['nit'])):
            return Response({'status': 'Brand already exist'}, status=status.HTTP_400_BAD_REQUEST)
        brand = Brand.objects.create(owner=request.user, name=data['name'], nit=data['nit'],
                                     prefix=generate_prefix(data['name']))
        serializer = BrandSerializer(brand)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request):
        queryset = Brand.objects.filter(owner=request.user)
        page = self.paginate_queryset(queryset)
        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['POST'])
    def massive_upload(self, request):
        data = request.data
        result = read_from_excel(data['excel'], data['photos'], data['brand_id'])
        return Response({'response': result}, status=status.HTTP_200_OK)


class Registration(viewsets.ModelViewSet):
    model = Brand
    queryset = model.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['POST'])
    def create_user(self, request):
        data = request.data
        user = User.objects.create_user(username=data['username'], password=data['password'],
                                        first_name=data.get('name', ''))
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
