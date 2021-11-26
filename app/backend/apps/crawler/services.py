import json
from datetime import timedelta
from random import randint

import requests
from django.db.models import Q

from .models import Debug
from ..item.models import Product
from ..item.serializers import ProductSerializer, ProductToPostSerializer
from ..user.models import Brand
from ..utils.constants import BASE_HOST, USER_AGENTS, IMAGE_FORMATS


def check_images_urls(optional_images, session):
    all_images = []
    for color in optional_images:
        images = []
        for image in color:
            if len(optional_images) == 1 or len(images) < 2:
                if url_is_image(image, session):
                    images.append(image)
        all_images.append(images)
    return all_images


def check_inactive_items(brand, started):
    inactive = Product.objects.filter(Q(brand=brand) & Q(updated__lt=started - timedelta(hours=6)))
    for item in inactive:
        item.active = False
        item.save()
    delete_from_remote([item.url for item in inactive])


def delete_from_remote(to_delete):
    if not type(to_delete) is list:
        to_delete = [to_delete]
    return requests.post(f'{BASE_HOST}/delete',
                         f'{{"data": {to_delete}}}'.replace("'", '"')).json()


def get_random_agent():
    return USER_AGENTS[randint(0, len(USER_AGENTS)) - 1]


def post_item(item):
    """Create or update the element with the same url"""
    data = ProductToPostSerializer(item).data
    for bf, af in (('reference', 'ref'), ('price_before', 'priceBefore'), ('price', 'allPricesNow'),
                   ('images', 'allImages'), ('sizes', 'allSizes'), ('original_category', 'originalCategory'),
                   ('original_subcategory', 'originalSubcategory'), ('national', 'nacional')):
        data[af] = data.pop(bf)
    data['nacional'] = 1 if data['nacional'] else 0
    name = data['name'][:29]
    data = json.dumps(data).encode('utf-8')
    Debug.objects.update_or_create(name=name, defaults={'text': str(data)})
    return requests.post(f'{BASE_HOST}/find', data)


def url_is_image(url, session=None):
    r = session.head(url) if session else requests.head(url)
    return r.headers["content-type"] in IMAGE_FORMATS
