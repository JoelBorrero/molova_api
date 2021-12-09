from django.contrib import admin
from django.conf.urls import include, url
from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view

from .apps.utils.views import *

router = DefaultRouter()
schema_view = get_swagger_view(title='Molova')

PREFIX_URL = settings.PREFIX_URL
urlpatterns = [
      url(r'^{}admin/'.format(PREFIX_URL), admin.site.urls),
      url(r'^{}auth/'.format(PREFIX_URL), include('rest_auth.urls')),
      url(r'^{}$'.format(PREFIX_URL), schema_view),
      url(r'^{}api/'.format(PREFIX_URL), include(router.urls)),
      url(r'^{}api/v1/crawler/'.format(PREFIX_URL), include('backend.apps.crawler.urls')),
      url(r'^{}api/v1/user/'.format(PREFIX_URL), include('backend.apps.user.urls')),
      path('views/brand', brand, name='brand'),
      path('views/crawl', crawl, name='crawl'),
      path('views/login', login, name='login'),
      path('views/products', product_list, name='products'),
      path('views/stats', stats, name='stats')
]

