import json
import os
from datetime import datetime, timedelta
from random import randint

import ast
import requests
from django.db.models import Q
from urllib.parse import quote

from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult

from .models import Debug
from ..item.models import Product
from ..item.serializers import ProductToPostSerializer
from ..utils.constants import BASE_HOST, IMAGE_FORMATS, TIMEZONE, USER_AGENTS


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


def get_last_process() -> dict:
    """Returns info about last crawling process executed"""
    result = TaskResult.objects.exclude(task='celery.backend_cleanup').last()
    status = 'Exitoso' if result.get_status_display() == 'SUCCESS' else 'Error'
    task = PeriodicTask.objects.filter(task=result.task).first()
    if task:
        name = task.name
        description = task.description
    else:
        name = 'Error'
        description = f'Task {result.task} not found'
    estimated = (datetime.now() - result.date_done.replace(tzinfo=None)).seconds
    return {'description': description, 'estimated': estimated, 'name': name, 'result': status}


def get_next_process() -> dict:
    """Returns info about next crawling process to be executed"""
    next_task = {}
    tasks = PeriodicTask.objects.all().exclude(name='celery.backend_cleanup')
    for task in tasks:
        description = task.description
        estimated = task.schedule.remaining_estimate(datetime.now(TIMEZONE)).seconds
        name = task.name
        if 'estimated' not in next_task or estimated < next_task['estimated']:
            next_task = {'description': description, 'estimated': estimated, 'name': name}
    return next_task


def get_random_agent() -> str:
    return USER_AGENTS[randint(0, len(USER_AGENTS)) - 1]


def get_session(brand='') -> requests.Session:
    """
    Returns a :class:`Session` for context-management, prepared with headers according to a specific brand.
    """
    session = requests.session()
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': get_random_agent()
    }
    if brand == 'Bershka':
        headers.update({
            'referer': 'https://www.bershka.com/',})
    elif brand == 'Blunua' or brand == 'Solúa':
        brand = brand.replace('ú', 'u').upper()
        headers = {'X-Shopify-Access-Token': os.environ.get(f'SHOPIFY_{brand}')}
    elif brand == 'Mango':
        headers.update({
            'referer': 'https://www.shop.mango.com/'})
    elif brand == 'Pull & Bear':
        headers.update({
            'accept-language': 'en-US,en;q=0.9,es-US;q=0.8,es;q=0.7',
            'content-type': 'application/json',
            'referer': 'https://www.pullandbear.com/',
            'sec-ch-ua-platform': '"macOS"'})
    elif brand == 'Stradivarius' or brand == 'Zara':
        headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'en-US,en;q=0.9',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1'})
    session.headers.update(headers)
    return session


def get_statistics() -> dict:
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


def parse_url(url) -> str:
    return quote(url.lower(), safe=':/?=')


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
        try:
            res = requests.post(f'{BASE_HOST}/find', data)
        except Exception as e:
            res = f'Error posting {e}'
        return res
    return False


def update_brand_links(brand: str):
    """Function to scrap categories and generate urls and endpoints for specific brand"""
    urls = []
    session = get_session(brand)
    if brand == 'Bershka':
        host = 'https://www.bershka.com'
        base_url = f'{host}/itxrest/2/marketing/store/45109565/40259535/spot?languageId=-5&spot=BK3_ESpot_I18N&appId=1'
        response = session.get(base_url).json()['spots'][4]['value'].split('ItxCategoryPage.')
        categories = []
        for i, category in enumerate(response):
            if '.title' in category and 'Home.title' not in category and 'mujer' in category.lower():
                category_id = category[:category.index('.')]
                if category_id not in str(categories) and ' |' in category:
                    # In this case, the url is not obtained, so a category name is saved instead.
                    name = category[category.index('.title=') + 7: category.index(' |')]
                    endpoint = f'{host}/itxrest/3/catalog/store/45109565/40259535/category/{category_id}/product?showProducts=false&languageId=-5'
                    if bool(session.get(endpoint).json()['productIds']):
                        urls.append([name, endpoint])
        urls.reverse()
    elif brand == 'Mango':
        url = 'https://shop.mango.com/services/menus/v2.0/header/CO'
        categories = session.get(url).json()['menus'][0]['menus']['1']
        for category in categories:
            if category['containsChilds']:
                for key in category['menus'].keys():
                    for cat in category['menus'][key]:
                        if 'link' in cat and 'https://' in cat['link']:
                            if cat['link'] not in urls:
                                retro_id = cat["retroId"]
                                try:
                                    retro_id = '&menu=' + retro_id[retro_id.index('|') + 1:].replace(':', ';')
                                except ValueError:
                                    retro_id = ''
                                urls.append([cat['link'],
                                             f'https://shop.mango.com/services/productlist/products/CO/she/{category["appId"]}/?idSubSection={cat["id"]}{retro_id}'])
            else:
                if category['link'] not in urls and 'https://' in category['link']:
                    # urls.append(category['link'])
                    print(category['link'])
    elif brand == 'Pull & Bear':
        host = 'https://www.pullandbear.com'
        base_url = f'{host}/itxrest/2/catalog/store/25009465/20309430/category?languageId=-5&typeCatalog=1&appId=1'
        res = session.get(base_url).json()['categories'][0]['subcategories']
        for category in res:
            for cat in category['subcategories']:
                if 'categoryUrl' in cat:
                    if cat['subcategories']:
                        for subcategory in cat['subcategories']:
                            if cat['id'] == subcategory['viewCategoryId']:
                                url = f'{host}/co/{cat["categoryUrl"]}'
                                endpoint = f'{host}/itxrest/3/catalog/store/25009465/20309430/category/{cat["id"]}/product?languageId=-5&showProducts=false&appId=1'
                                urls.append([url, endpoint])
                    else:
                        url = f'{host}/co/{cat["categoryUrl"]}'
                        endpoint = f'{host}/itxrest/3/catalog/store/25009465/20309430/category/{cat["id"]}/product?languageId=-5&showProducts=false&appId=1'
                        urls.append([url, endpoint])
    elif brand == 'Stradivarius':
        url = 'https://www.stradivarius.com/itxrest/2/catalog/store/55009615/50331093/category?languageId=-48&typeCatalog=1&appId=1'
        res = session.get(url).json()['categories'][0]
        p1 = 'https://www.stradivarius.com'
        p2 = res['name']
        res = res['subcategories']
        for category in res:
            for cat in category['subcategories']:
                if cat['name'] == 'Ver todo':
                    url = f'{p1}/co/{p2}/{category["name"]}/{cat["name"]}-c{cat["id"]}.html'.lower().replace(' ', '-')
                    endpoint = f'{p1}/itxrest/2/catalog/store/55009615/50331093/category/{cat["id"]}/product?languageId=-48&appId=1'
                    urls.append([parse_url(url), endpoint])
                elif cat['subcategories']:
                    for c in cat['subcategories']:
                        if c['viewCategoryId']:
                            for subcategory in c['subcategories']:
                                if subcategory['id'] == c['viewCategoryId']:
                                    url = f'{p1}/co/{p2}/{category["name"]}/{cat["name"]}/{c["name"]}/{subcategory["name"]}-c{c["id"]}.html'.lower().replace(
                                        ' ', '-')
                                    endpoint = f'{p1}/itxrest/2/catalog/store/55009615/50331093/category/{subcategory["id"]}/product?languageId=-48&appId=1'
                                    urls.append([parse_url(url), endpoint])
    elif brand == 'Zara':
        host = 'https://www.zara.com/co/es'
        res = session.get(f'{host}/categories?ajax=true').json()['categories'][0]['subcategories']
        for category in res:
            for cat in category['subcategories']:
                if 'seo' in cat and cat['layout'] == 'products-category-view':
                    if cat['subcategories']:
                        for subcategory in cat['subcategories']:
                            if cat['redirectCategoryId'] == subcategory['id']:
                                url = f'{host}/{cat["seo"]["keyword"]}-l{cat["seo"]["seoCategoryId"]}.html?v1={subcategory["id"]}'
                                endpoint = f'{host}/category/{subcategory["id"]}/products?ajax=true'
                                urls.append([url, endpoint])
                    else:
                        url = f'{host}/{cat["seo"]["keyword"]}-l{cat["seo"]["seoCategoryId"]}.html?v1={cat["id"]}'
                        endpoint = f'{host}/category/{cat["id"]}/products?ajax=true'
                        urls.append([url, endpoint])
    settings = ast.literal_eval(open('Settings.json', 'r').read())
    settings[brand]['endpoint'] = urls[0][1]
    settings[brand]['endpoints'] = urls
    with open('Settings.json', 'w') as s:
        s.write(str(settings).replace("'", '"'))


def bershka_endpoint_maker(urls, save=True):
    """
    Manual mode to modify Bershka urls and generate endpoints
    """
    output = []
    for url in urls:
        category_id = url[url.rindex('-c') + 2:url.rindex('.html')]
        endpoint = f'https://www.bershka.com/itxrest/3/catalog/store/45109565/40259535/category/{category_id}/product?showProducts=false&languageId=-5'
        output.append([url, endpoint])
    if save:
        settings = ast.literal_eval(open('Settings.json', 'r').read())
        settings['Bershka']['endpoint'] = urls[0][1]
        settings['Bershka']['endpoints'] = urls
        with open('Settings.json', 'w') as s:
            s.write(str(settings).replace("'", '"'))
    return output


def url_is_image(url, session=None) -> bool:
    """Verify if a url is image"""
    r = session.head(url) if session else requests.head(url)
    return r.headers["content-type"] in IMAGE_FORMATS
