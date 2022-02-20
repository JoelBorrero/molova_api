import json
from datetime import datetime, timedelta
from random import randint

import ast
import os
import requests
from django.db.models import Q
from django_celery_beat.models import PeriodicTask
from urllib.parse import quote

from .models import Debug
from ..item.models import Product
from ..item.serializers import ProductSerializer, ProductToPostSerializer
from ..user.models import Brand
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


def get_next_process():
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


def parse_url(url):
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


def update_brand_links(brand):
    """Function to scrap categories and generate urls and endpoints for specific brand"""
    urls = []
    session = requests.session()
    if brand == 'Bershka':
        host = 'https://www.bershka.com'
        base_url = f'{host}/itxrest/2/marketing/store/45109565/40259535/spot?languageId=-5&spot=BK3_ESpot_I18N&appId=1'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cookie': 'ITXSESSIONID=3ee14ba34dfc995d70db354ab8080761; BSKSESSION=978fe558a1d558033c5ca231238f8bca; AKA_A2=A; bm_sz=7638EA7910C89DA7119EB6D817AFD079~YAAQtqpLaDKLFnF+AQAA5vxedA4mr9yHZTRY8+QkTBtYqIvmVYOgevGRAK3l6uzPOoivM5DNvYtAQ5hiMmrD4iNUdhnVs9QnX8ddPtPR/kHILHWqaG16pRWBczAl5bJ3gSn5cZorioF7lkexiN6bxlLhWTAtLAa8QySBAg6IEjMLIxW4MEe7+NMb0XvwIFJqHPI2YOuWdIELWBrknJRF+r+I7dgB9WGQZdu2FeK0UhJrfcRrYU4mUkipGj2gjiU9LXcYKuSUK3O7QgpXczRTSvAI8mePBSVxHZhwCrXn3s8rxe+b~4538677~3488049; _abck=E3CA12B51EA31D4931269A3B9CBF6479~0~YAAQtqpLaLaLFnF+AQAASgRfdAfMSetcUwuLid+BWUyLmKkG3+65ZdtTC5NdHPPUMzOD+dJ+1Hex8mcmgM4AEV2dUuIseZKi2wLtiRTfj09Pu6ucr9eP3gbLDXSeNren5j75eiwrJ2g15tl7V5isX58qezMclw3GulVdadqD7QWzo8BqAuCRQhN7CesREQwk5y4KIQbDT793IPLd0UJDR8/xeSuxL35+8D+LOOuORgdWxy/7atr2mPnkcYNbraz4z/90spYpIOp5xRIACWEnxexnOQP6MThxZKItKFM5oFm5EgSDRhW4RKONFghIEpb7bD+Wquf/iBgfranSB/cJTc8QwIeh8dIL5K6B+63zTZGq6U46m+yKAEg1GdikWpZXFQTDzCtpor55Jl3Hq4APrj8pCn8NfhrDaQ==~-1~-1~-1; ak_bmsc=C9E13B72C3BB3F83107B139FA7A5FD30~000000000000000000000000000000~YAAQtqpLaOCLFnF+AQAALQdfdA6bK8hfLeKAHZG79vyEJrDU8EbvM+FfVY/S+5+8Xa9F8H2oc0eguQ0iloJeSLxBHCzAOvXqn/E5Sj2BhA1z/hsxJHoNPYj4J/hGuiQ18iN2epB6lPycJJU4FFtSJD2mB4Aow/l4Gm0JRCmsg9J51GPbFohxDhMrmbTZp8dOMZ7BSlt6ByRvbyZSyEoXkHGA13EuyQiPRI0ZB9Z7GmfE8ewO5HwjEFZX0Mq+/Gd/xTo79JQlAuZZJq5DdOYo1jWO6BtnSSN+JV3WSomwwpuS5JsQgj6sCvbndqNJ5DvcMk6ZJc7nI/ELxqrcn3Glnmj3vU7SQZWOH2AcSmua1aCWVwVBLLwEBhCneQFfedbC8ynQWJk8jxsVQEnYXSbZFeqkHwKmH4WUhZig5cgBt7/Hebp4hyD0jy7Ia+i7sdhf7j9gEcegMU8Cxyn/6HofhwM8GsjVk6c+H2IGOfXrCh6mYFuXy3Bdo94=; JSESSIONID=0000p-aooDS7zImjpP9lRM6PCLt:2bb5bu1sx; 13d5823230c8607ca960f5962192c9e2=50e00281f36d1947da8664796a34091f; OptanonConsent=isIABGlobal=false&datestamp=Wed+Jan+19+2022+17:08:16+GMT-0500+(Colombia+Standard+Time)&version=6.8.0&hosts=&consentId=575fe5a6-ee00-403f-8b32-ae2c810ae690&interactionCount=1&landingPath=NotLandingPage&groups=C0001:1,C0003:1,C0002:1,C0004:1&geolocation=CO;BOL&AwaitingReconsent=false; OptanonAlertBoxClosed=2022-01-19T22:08:16.149Z',
            'content-type': 'application/json',
            'referer': 'https://www.bershka.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': get_random_agent()}
        session.headers.update(headers)
        response = session.get(base_url).json()['spots'][4]['value'].split('ItxCategoryPage.')
        categories = []
        for i, category in enumerate(response):
            if '.title' in category and 'Home.title' not in category and 'mujer' in category.lower():
                category_id = category[:category.index('.')]
                if category_id not in str(categories) and ' |' in category:
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
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9,es-US;q=0.8,es;q=0.7',
            'content-type': 'application/json',
            'referer': 'https://www.pullandbear.com/',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': get_random_agent()}
        session.headers.update(headers)
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
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'es-US,es;q=0.9',
            'content-type': 'application/json',
            'cookie': 'ITXSESSIONID=182592649f55aa1d98689723945fba3c; _abck=98D0A42A991781EA9192E81AB1B3DA3F~-1~YAAQT/1Vvs+'
                      '4hLh6AQAAeqNzSgaJEW8ixKACFBQiOORFishd5S4Qz7WkGyAvA0LNo/wTMQ4S6a5NkeaLagHp/t9Zbk9B6ga2UTgMBMhrC0rtyMi'
                      'rxcWjDCX8+hXQRF5Eex8lXYCu4V7H7HyTvSBPuK29LvIW3aFHvmqxw17hbJBndu67nAhdmxNNZ7r7wuqF861oo9dVhzLHYbhiBjP'
                      'UmuOr5x22PV8HNtU3a15bH/pTOp/86mPMTWdWmmsO40hy/cFHprjRPILbrZqtt5zsZ46U6d+ODU2pGvwyvOXyIwQ4rSrPcBKcgmU'
                      'w6Dtq/GBqlVzS9wfKc5RsbjAvn2anQyRSLhdS2ClIRGBc7knewLNuoBXxNrPFq3lPzdt5uXs=~-1~-1~-1; ak_bmsc=DD61DFF3'
                      'B5C9D1B3E4463FEA8F6BDEC3~000000000000000000000000000000~YAAQT/1VvtC4hLh6AQAAeqNzSgzQJDKMApzD4ibQ2yO5'
                      'D+QCMRHgTZRmSgabRaqtAeQTyqfPc0D1k3m0S66Jr5kvkwDl1rr1NNCyBLA+jZ83hwbE3Oq2KmOponQVKwsCHqbtQVS7W9Ne7/8k'
                      'mLznO6z2fbKXtMG8Zntc+aeqY4eJ46PIzSdQPjrIoFu5zqPAOEbnSa99LDEcuJpIErezw5E+EDrbrh8n0OnL5xHzyiyTMYrq9uPK'
                      'MfzzpM4NDUovIBvvN0TwGcDU0b6Ju+UlF9cqiMUhMaoLZCXw+RcFF/4aAhpstC8h5gJa4BCk/P7EIeBpOFJg9nKgWeqiP6Hkhh46'
                      'mn3XN67SPHCt4/3iyVYumSCtiKryOQktUcVzkEO9V30=; bm_sz=972FA142E752B8D15050CD920326B68B~YAAQT/1VvtG4hLh'
                      '6AQAAeqNzSgzXXX/95f+VvKgIwgtfU2OQW+ZMBBTicVhdB7msgrQ1jZ+P5pI1kwmpg3hmAD/29FxFdJTtw6yQTmmoLL8J2d2ZJj6'
                      'JryxZIjM1uqDkZ7gy1mIP8kKwn61leSzqsZvRD+Zc5wYav5rroxMeNcFT0InjGA+juZx8ZtWfZ1PI5fD2iK1fDhUoZxcLAHJc5AL'
                      'WycjN/fqV8WpnA+YJKNJVr7ePQncd0aNN3tLJGptKK49ts8dEtjYh2GbwUhuRRO5NQJCGvdpcpdjhTtruOEjQgrgevMA7naI=~34'
                      '91394~3425845',
            'referer': 'https://www.stradivarius.com/',
            'user-agent': get_random_agent()}
        session.headers.update(headers)
        res = session.get(url).json()['categories'][0]
        p1 = 'https://www.stradivarius.com'
        p2 = res['name']
        id = res['id']
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
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': get_random_agent()}
        session.headers.update(headers)
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
        settings[brand]['endpoint'] = urls[0][1]
        settings[brand]['endpoints'] = urls
        with open('Settings.json', 'w') as s:
            s.write(str(settings).replace("'", '"'))
    return output


def url_is_image(url, session=None) -> bool:
    """Verify if a url is image"""
    r = session.head(url) if session else requests.head(url)
    return r.headers["content-type"] in IMAGE_FORMATS
