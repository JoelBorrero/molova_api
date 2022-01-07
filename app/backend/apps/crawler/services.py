import json
from datetime import timedelta
from random import randint

import ast
import os
import requests
import urllib.parse
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


def parse_url(url):
    return urllib.parse.quote(url.lower(), safe=':/')


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
    urls = []
    session = requests.session()
    if brand == 'Bershka':
        pass
    elif brand == 'Mango':
        url = 'https://shop.mango.com/services/menus/v2.0/header/CO'
        categories = requests.get(url).json()['menus'][0]['menus']['1']
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
        base_url = 'https://www.pullandbear.com/itxrest/2/catalog/store/25009465/20309430/category?languageId=-5&typeCatalog=1&appId=1'

    elif brand == 'Stradivarius':
        url = 'https://www.stradivarius.com/itxrest/2/catalog/store/55009615/50331093/category?languageId=-48&typeCatalog=1&appId=1'
        session = requests.session()
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
        res = res['subcategories']
        for category in res:
            for cat in category['subcategories']:
                for c in cat['subcategories']:
                    if c['subcategories']:
                        for subcategory in c['subcategories']:
                            if c['viewCategoryId'] == subcategory['id']:
                                url = f'{p1}/co/{p2}/{category["name"]}/{cat["name"]}/{c["name"]}-c{c["id"]}.html'.replace(' ', '-')
                                urls.append([parse_url(url), f'{p1}/itxrest/2/catalog/store/55009615/50331093/category/{subcategory["id"]}/product?languageId=-48&appId=1'])
                    else:
                        url = f'{p1}/co/{p2}/{category["name"]}/{cat["name"]}/{c["name"]}-c{c["id"]}.html'.replace(' ', '-')
                        urls.append([parse_url(url), f'{p1}/itxrest/2/catalog/store/55009615/50331093/category/{c["id"]}/product?languageId=-48&appId=1'])
    elif brand == 'Zara':
        session = requests.session()
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'cookie': 'ITXSESSIONID=d458e4b17f001e37dfdd0cc93fbe1717; web_version=STANDARD; bm_sz=B77396026A92E8F97FA258393551A02E~YAAQpKpLaP3Jm7R6AQAAMbyEvg2KTcnl6zbnIQp+bZr8QZF8eXTyts74BzbwCO5yOYGfgrQ1IK/ZtgBxEIdaxz/4vh4DW3DjZOvD6jMhLg7HWKxSEJLwRG3QE9en2at6n104IgL8ncgIML9rNJfv9bzJoKScK+FbZnG9Xav64FI9U850vPuzCcC2Q7yluiPX1McNYw0glOBo7TH6dO5feI2rFAWAJJfHv6Y2eQ6gYu46OZ7vOanrBwTi4HaeVptV80R+3gLetroqBfLaWXZIIT82hBO90y27hL8JeHD/HtE0~3424833~4273222; _abck=AD1BE4EBB69FA500FE0C71CB433A60B0~0~YAAQpKpLaAPKm7R6AQAAj8GEvgZ+SRGl6rrPLN5AeYGCRe76FBuhKFLzvcf3qD+YdOCRYAq2AO4JgUfWq00iE7KWe9B8TeKUqodFqzD/yAoJrN+LvAfwmmP5mO+hPcndGJYxcSWBTUZRrzFyR8labOPBk04SMr6ie4QMrOtjwfo8W8vG9PDex8FGoZhZqcE4Qu10CbBlOpzcumdc0ka6X2L/D2XMfq19EyBgvRiWSKHCHZOC6R4SxI8z1VrDxGvpcdxDNSq+UzOWpjPuV8xRJwQfoKfItmWWPzEcPn3OF2mwQGhHy6JUaE/mIF1ldde8qpRz38KFsrLYX2n+Htlim5tgX0gLSo1UhSmYgVDXx/KbM2Yr0l5ImcUGgNE2lCZsj6hJ5tQT12ARz8zv/FBvQZxCmNiFaw==~-1~-1~-1; ak_bmsc=8329DA2709C86864C6E40D3ACBA821AE~000000000000000000000000000000~YAAQpKpLaAvKm7R6AQAAP8WEvg33e6w414subhHXC3mgw6uB3YZvjS22aPHbCCOR2laB3AF2hINX/nG2ud2aPU/v5/kJFsIbuoaI5WTCKYiqIyJEks63rvazFKn4okA8r5u/Q0pvGUpPz/L8GdmTOHxrU7cvHqltA5MS/nD0C1Ctt6TXz0M1kmZKBOEJHmlPH1mQPoNiZQVieRSO4+bk4Im9ml5yO691ogvDxw//dHwUd4xvWylRyyHAqTl89Mbar93V2xmKl/ANvdzPRwtzdFxVameqNjlL+nYLPAlPNxsLfKPKcKjHhl45G5iAtcMbc5BahKLAwQ4QuutHfVnFWaWANAO7UH1v7h1kOT5LqM8L+bTryXq0xWUSLpL/R6D++Uaz1J69mEfisXiH5VVeyHtXiInPxYiucKayF5bLUE60rCT9fSsVfb8zxwRkdaPx4AQ+Vdhcc/X6ujcubVnBZyyrh4j3OhxF+ZmUsOcrZmEr9wrTpxpN/w==; rid=61e5ec44-e21e-4a15-a356-817a5015c536; vwr_global=1.1.1630988978.b8630a30-29c8-4f68-a346-56eeff82262b.1630988978..M4EHYfBDQijUPEKmwTyNXh4yy6_bS2cOX-QOKMWkhow; storepath=co%2Fes; cart-was-updated-in-standard=true; rskxRunCookie=0; rCookie=jo27kadi1hlmxxaul4r3kt9kq6n1; chin={"status":"chat-status:not_connected","isChatAttended":false,"privacyAccepted":false,"email":"","userJid":"","uiCurrentView":"view:hidden","timeShowInteractiveChat":0,"compatMode":true,"businessKind":"online"}; lastRskxRun=1630988990053; _ga=GA1.2.1818226498.1630988991; _gid=GA1.2.237491462.1630988991; _fbp=fb.1.1630988991038.1662346990; _gat_UA-18083935-1=1; OptanonConsent=isIABGlobal=false&datestamp=Mon+Sep+06+2021+23%3A29%3A51+GMT-0500+(Colombia+Standard+Time)&version=6.8.0&hosts=&consentId=a9608d84-85af-48dd-b839-cfa5e1d8d766&interactionCount=1&landingPath=https%3A%2F%2Fwww.zara.com%2Fco%2Fes%2Fmujer-nuevo-l1180.html%3Fv1%3D1881787&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1; RT="z=1&dm=zara.com&si=38791a9a-8027-4374-94b3-e222789fe077&ss=kt9kq31v&sl=4&tt=emy&bcn=%2F%2F17c8edc7.akstat.io%2F&ld=dz3&ul=y6f&hd=ycs"; _ga_D8SW45BC2Z=GS1.1.1630988990.1.0.1630989019.31',
            'pragma': 'no-cache',
            'referer': 'https://www.zara.com/co/',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
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


def url_is_image(url, session=None) -> bool:
    r = session.head(url) if session else requests.head(url)
    return r.headers["content-type"] in IMAGE_FORMATS
