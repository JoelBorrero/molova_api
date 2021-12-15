import json
from datetime import timedelta
from random import randint

import ast
import requests
from django.db.models import Q

from .models import Debug
from ..item.models import Product
from ..item.serializers import ProductSerializer, ProductToPostSerializer
from ..user.models import Brand
from ..utils.constants import BASE_HOST, USER_AGENTS, IMAGE_FORMATS


def check_images_urls(optional_images, session=None) -> list:
    """
    @param optional_images: A nested list of possibles image urls
    @param session: A requests session to avoid using multiple individual requests
    @return: A nested list clean without broken links
    """
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
    inactive = Product.objects.filter(Q(brand=brand) & Q(updated__lt=started - timedelta(hours=6)) & Q(active=True))
    for item in inactive:
        item.active = False
        item.save()
    delete_from_remote([item.url for item in inactive])


def delete_from_remote(to_delete: list):
    if not type(to_delete) is list:
        to_delete = [to_delete]
    return requests.post(f'{BASE_HOST}/delete',
                         f'{{"data": {to_delete}}}'.replace("'", '"')).json()


def get_random_agent():
    return USER_AGENTS[randint(0, len(USER_AGENTS)) - 1]


def get_statistics():
    output = {}
    keys = ['Camisas y Camisetas', 'Pantalones y Jeans', 'Vestidos y Enterizos', 'Faldas y Shorts', 'Abrigos y Blazers',
            'Ropa deportiva', 'Zapatos', 'Bolsos', 'Accesorios']
    for last in keys:
        for index in [0, 1]:
            endpoint = f'{BASE_HOST}/coleccion/{index}/{last}'.replace(' ', '%20')
            res = requests.get(endpoint).json()
            if 'items' in res:
                for item in res['items']:
                    brand = item['brand']
                    if brand not in output:
                        output[brand] = {'col': {}, 'sale': {}}
                        for key in keys:
                            output[brand]['col'][key] = 0
                            output[brand]['sale'][key] = 0
                    if item['sale']:
                        output[brand]['sale'][item['category']] += 1
                    else:
                        output[brand]['col'][item['category']] += 1
    Debug.objects.update_or_create(name='Statistics', defaults={'text': str(output)})
    return output


def post_item(item):
    """Create or update the element with the same url on remote db"""
    try:
        all_sizes = ast.literal_eval(item.sizes)
        if not all_sizes:
            all_sizes = [['']]
    except (SyntaxError, ValueError):
        all_sizes = [['']]
    active = not all([all(['(AGOTADO)' in size for size in sizes]) for sizes in all_sizes])
    if active:
        data = ProductToPostSerializer(item).data
        for bf, af in (('reference', 'ref'), ('price_before', 'priceBefore'), ('price', 'allPricesNow'),
                       ('images', 'allImages'), ('sizes', 'allSizes'), ('original_category', 'originalCategory'),
                       ('original_subcategory', 'originalSubcategory'), ('national', 'nacional')):
            data[af] = data.pop(bf)
        data['nacional'] = 1 if data['nacional'] else 0
        # name = data['name'][:29]
        data = json.dumps(data).encode('utf-8')
        # Debug.objects.update_or_create(name=name, defaults={'text': str(data)})
        return requests.post(f'{BASE_HOST}/find', data)
    return False


def url_is_image(url, session=None) -> bool:
    r = session.head(url) if session else requests.head(url)
    return r.headers["content-type"] in IMAGE_FORMATS
