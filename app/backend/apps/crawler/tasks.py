from datetime import datetime, timedelta
from random import randint
from time import sleep
from urllib.parse import quote

import requests
from celery import shared_task

from .models import Process, Debug  # , Settings
from .services import get_random_agent, post_item, check_images_urls, check_inactive_items, delete_from_remote
from ..item.models import Product
from ..item.services import find_product, get_category, get_subcategory, get_colors_src, create_or_update_item
from ..utils.constants import SETTINGS


# settings = Settings.objects.all().first()
# if not settings:
#     settings = settings.objects.create()[0]


#  TODO Verify stock to inactive, brands needs approval and products also
@shared_task
def crawl_bershka():
    brand = 'Bershka'
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(),
        'logs': f'··········{datetime.now().month} - {datetime.now().day}··········\n'})[0]
    session = requests.session()
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'referer': 'https://www.bershka.com/',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': get_random_agent()}
    session.headers.update(headers)
    for endpoint in SETTINGS[brand]['endpoints'][-5:-4]:
        products = session.get(endpoint[1]).json()['products']
        self.logs += f'{datetime.now().hour}:{datetime.now().minute}  -  {len(products)} productos  -  {endpoint[0]}\n'
        for product in products:
            try:
                name = product['name']
                prod_id = product['id']
                original_category = product['relatedCategories'][0]['name']
                category = get_category(brand, name, original_category)
                product = product['bundleProductSummaries'][0]['detail']
                description = product['description'] if product['description'] else product['longDescription']
                ref = product['displayReference']
                original_subcategory = product['subfamilyInfo']['subFamilyName']
                subcategory = get_subcategory(brand, name, category, original_subcategory)
                url = f'https://www.bershka.com/co/{name.lower().replace(" ", "-")}-c0p{prod_id}.html'
                colors, all_images, all_sizes = [], [], []
                for color in product['colors']:
                    colors.append(
                        f'https://static.bershka.net/4/photos2{color["image"]["url"]}_2_4_5.jpg'
                        f'?t={color["image"]["timestamp"]}')
                    sizes = []
                    for size in color['sizes']:
                        stock = '' if size['visibilityValue'] == 'SHOW' else '(AGOTADO)'
                        sizes.append(size['name'] + stock)
                    all_sizes.append(sizes)
                price_now = int(product['colors'][0]['sizes'][0]['price']) / 100
                try:
                    price_before = int(product['colors'][0]['sizes'][0]['oldPrice']) / 100
                except TypeError:
                    price_before = price_now
                discount = 100 - int(price_now / price_before * 100)
                optional_images = []
                for media in product['xmedia']:
                    color = []
                    for i in media['xmediaItems'][0]['medias']:
                        if '_2_6_' not in i['idMedia']:
                            color.append(
                                f'https://static.bershka.net/4/photos2/{media["path"]}/{i["idMedia"]}3.jpg'
                                f'?ts={i["timestamp"]}')
                    optional_images.append(color)
                item = find_product(url, optional_images)
                active = not all([all(['(AGOTADO)' in size for size in sizes]) for sizes in all_sizes])
                fields = {'name': name, 'reference': ref, 'description': description, 'url': url,
                          'price_now': price_now, 'price_before': price_before, 'discount': discount,
                          'sale': bool(discount), 'sizes': all_sizes, 'colors': get_colors_src(colors),
                          'category': category, 'original_category': original_category, 'subcategory': subcategory,
                          'original_subcategory': original_subcategory, 'gender': 'm', 'active': active}
                item = create_or_update_item(item, fields, optional_images, session)
                self.logs += f'    + {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {name}\n'
                if item.active:
                    post_item(item)
            except Exception as e:
                self.logs += f'X {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {e}\n'
        self.save()
        headers = session.headers
        sleep(randint(30, 120) / 1)  # settings.speed)
        session = requests.session()
        session.headers.update(headers)
    check_inactive_items(brand, self.started)


@shared_task
def crawl_stradivarius():
    brand = 'Stradivarius'
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(),
        'logs': f'··········{datetime.now().month} - {datetime.now().day}··········\n'})[0]
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
    for endpoint in SETTINGS[brand]['endpoints']:
        products = session.get(endpoint[1]).json()['products']
        self.logs += f'{datetime.now().hour}:{datetime.now().minute}  -  {len(products)} productos  -  {endpoint[0]}\n'
        for product in products:
            # try:
            ref = f'{product["detail"]["displayReference"]}'
            original_category = str(product['detail']['familyInfo']['familyName'])
            original_subcategory = str(product['detail']['subfamilyInfo']['subFamilyName'])
            prod_id = product['id']
            # try:
            cat_id = product['relatedCategories'][0]['id']
            # except:
            #     cat_id = '12345'
            # try:
            product = product['bundleProductSummaries'][0]
            # except:
            #     pass
            name = product['name']
            category = get_category(brand, name, original_category)
            subcategory = get_subcategory(brand, name, category, original_subcategory)
            product = product['detail']
            description = product['description']
            price_now = int(product['colors'][0]['sizes'][0]['price']) / 100
            try:
                price_before = int(product['colors'][0]['sizes'][0]['oldPrice']) / 100
            except TypeError:
                price_before = price_now
            discount = int(100 - price_now / price_before * 100)
            url = f'{endpoint[0][:endpoint[0].index("-c")]}/{quote(name.lower().replace(" ", "-"))}-c{cat_id}p{prod_id}.html'
            all_images, all_sizes, colors = [], [], []
            for color in product['colors']:
                sizes = []
                if color['image']:
                    image = f'https://static.e-stradivarius.net/5/photos3{color["image"]["url"]}_3_1_5.jpg' \
                            f'?t={color["image"]["timestamp"]}'
                    colors.append(image)
                for size in color['sizes']:
                    stock = ''
                    if 'visibilityValue' in size and not size['visibilityValue'] == 'SHOW':
                        stock = '(AGOTADO)'
                    sizes.append(f'{size["name"]} {stock}')
                all_sizes.append(sizes)
            optional_images = []
            for media in product['xmedia']:
                color = []
                for i in media['xmediaItems'][0]['medias']:
                    color.append(
                        f'https://static.e-stradivarius.net/5/photos3{media["path"]}/{i["idMedia"]}2.jpg'
                        f'?t={i["timestamp"]}')
                optional_images.append(color)
            item = find_product(url, optional_images)
            active = not all([all(['(AGOTADO)' in size for size in sizes]) for sizes in all_sizes])
            fields = {'brand': brand, 'name': name, 'reference': ref, 'description': description, 'url': url,
                      'price_now': price_now, 'price_before': price_before, 'discount': discount,
                      'sale': bool(discount), 'sizes': all_sizes, 'colors': get_colors_src(colors),
                      'category': category, 'original_category': original_category, 'subcategory': subcategory,
                      'original_subcategory': original_subcategory, 'gender': 'm', 'active': active}
            item = create_or_update_item(item, fields, optional_images, session)
            self.logs += f'    + {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {name}\n'
            if item.active:
                post_item(item)
            else:
                Debug.objects.create(name='no_stock', text=item)
            # except Exception as e:
            #     self.logs += f'X {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {e}\n'
            #     Debug.objects.create(text=e, name='Error STR')
        self.save()
        headers = session.headers
        sleep(randint(30, 120) / 1)
        session = requests.session()
        session.headers.update(headers)
    check_inactive_items(brand, self.started)
