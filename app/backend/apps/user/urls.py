from django.urls import path, include
from rest_framework import routers
from . import viewsets

router = routers.DefaultRouter()
router.register(r'brand', viewsets.BrandViewSet, basename='brand')
# router.register(r'register', viewsets.Registration, basename='register')
urlpatterns = [
    path(r'', include(router.urls))
]
