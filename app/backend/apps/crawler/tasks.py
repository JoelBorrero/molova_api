import os
from datetime import datetime, timedelta
from random import randint
from time import sleep

import ast
import requests
from celery import shared_task

from .models import Process, Debug
from .services import get_random_agent, post_item, check_images_urls, check_inactive_items, delete_from_remote, \
    parse_url
from ..item.models import Product
from ..item.services import find_product, get_category, get_subcategory, get_colors_src, create_or_update_item, \
    to_int, calculate_discount
from ..user.models import Brand
from ..utils.constants import BASE_HOST, SETTINGS, TIMEZONE


# Subcategoría: Vestidos
# Color: azul, verde
# Estampado: liso, lunares, flores, lentejuelas
# Ocasión: Fiesta, Playa
# Material: Seda, Lino, licra
# Corte: Corto, Largo, Midi
# Clima: cálido, frío, templado
# Marca: Zara, Molú, Mango
# Valores: hecho en Colombia, moda lenta, moda consciente
# Precio: menos de 50.000, rango

@shared_task
def crawl_bershka():
    brand = 'Bershka'
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(TIMEZONE),
        'status': 'x',
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
    page_size = 25
    try:
        for endpoint in SETTINGS[brand]['endpoints']:
            category_id = endpoint[1][endpoint[1].index('/category/') + 10: endpoint[1].rindex('/')]
            response = session.get(endpoint[1]).json()['productIds']
            self.logs += f'{datetime.now().hour}:{datetime.now().minute}  -  {len(response)} productos  -  {endpoint[0]}\n'
            self.save()
            for page in range(len(response) // page_size):
                ids = [prod_id for prod_id in response[page * page_size: (page + 1) * page_size]]
                page_endpoint = f'https://www.bershka.com/itxrest/3/catalog/store/45109565/40259535/productsArray?categoryId={category_id}&productIds={str(ids)[1:-1].replace(", ", "%2C")}&languageId=-5'
                products = session.get(page_endpoint).json()['products']
                for product in products:
                    name = product['name']
                    if name:
                        try:
                            prod_id = product['id']
                            original_category = product['relatedCategories'][0]['name']
                            category = get_category(brand, name, original_category)
                            if product['bundleProductSummaries']:
                                product = product['bundleProductSummaries'][0]['detail']
                            else:
                                product = product['detail']
                            description = product['description'] if product['description'] else product[
                                'longDescription']
                            ref = product['displayReference']
                            original_subcategory = product['subfamilyInfo']['subFamilyName']
                            if not original_subcategory:
                                original_subcategory = product['familyInfo']['familyName']
                            subcategory = get_subcategory(brand, name, category, original_subcategory)
                            url = f'https://www.bershka.com/co/{name.lower().replace(" ", "-")}-c0p{prod_id}.html'
                            all_images, all_sizes, colors, color_styles = [], [], [], []
                            for color in product['colors']:
                                colors.append(
                                    {'name': color['name'],
                                     'picture': f'https://static.bershka.net/4/photos2{color["image"]["url"]}_2_4_5.jpg?t={color["image"]["timestamp"]}'})
                                if color['image']['style']:
                                    color_styles.append(f'{color["image"]["style"][0]}/')
                                else:
                                    color_styles.append('')
                                sizes = []
                                for index, size in enumerate(color['sizes']):
                                    stock = '' if size['visibilityValue'] == 'SHOW' else '(AGOTADO)'
                                    tag = size['name'] + stock
                                    if size['name'] not in sizes and tag not in sizes:
                                        sizes.append(tag)
                                all_sizes.append(sizes)
                            price_now = int(product['colors'][0]['sizes'][0]['price']) / 100
                            try:
                                price_before = int(product['colors'][0]['sizes'][0]['oldPrice']) / 100
                            except TypeError:
                                price_before = price_now
                            discount = calculate_discount(price_before, price_now)
                            while len(color_styles) < len(product['xmedia']):
                                color_styles.append(color_styles[-1])
                            optional_images = []
                            for index, media in enumerate(product['xmedia']):
                                color = []
                                for i in media['xmediaItems'][0]['medias']:
                                    if '_2_6_' not in i['idMedia']:
                                        color.append(
                                            f'https://static.bershka.net/4/photos2/{media["path"]}/{color_styles[index]}{i["idMedia"]}3.jpg'
                                            f'?ts={i["timestamp"]}')
                                optional_images.append(color)
                            item = find_product(url, optional_images)
                            active = not all([all(['(AGOTADO)' in size for size in sizes]) for sizes in all_sizes])
                            fields = {'brand': brand, 'name': name, 'reference': ref, 'description': description,
                                      'url': url,
                                      'id_producto': url, 'price': price_now, 'price_before': price_before,
                                      'discount': discount,
                                      'sale': bool(discount), 'sizes': all_sizes, 'colors': get_colors_src(colors),
                                      'category': category, 'original_category': original_category,
                                      'subcategory': subcategory,
                                      'original_subcategory': original_subcategory, 'gender': 'm', 'active': active,
                                      'national': False}
                            item = create_or_update_item(item, fields, session, optional_images=optional_images)
                            if item.active:
                                # self.logs += f'    + {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {name}\n'
                                post_item(item)
                            else:
                                self.logs += f'\nX NO STOCK {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second} - {url}\n'
                        except Exception as e:
                            self.logs += f'X {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {e}\n'
            self.save()
            headers = session.headers
            # sleep(randint(30, 120) / 1)  # settings.speed)
            session = requests.session()
            session.headers.update(headers)
        self.status = 's'
        self.save()
        check_inactive_items(brand, self.started)
    except Exception as e:
        self.status = 'f'
        self.save()
        raise e


@shared_task
def crawl_blunua():
    brand = 'Blunua'
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(TIMEZONE),
        'status': 'x'
    })[0]
    session = requests.session()
    session.headers = {'X-Shopify-Access-Token': os.environ.get('SHOPIFY_BLUNUA')}
    url = 'https://blunua-jewelry.myshopify.com/admin/api/2021-10/products.json?limit=250&fields=id,title,variants,' \
          'images,product_type,body_html,status,handle'
    try:
        products = session.get(url).json()['products']
        now = datetime.now()
        self.logs = f'··········{now.month} - {now.day}··········\n{len(products)} productos\n'
        for p in products:
            now = datetime.now()
            url = f'https://blunua.com/products/{p["handle"]}'
            active = any([v['inventory_quantity'] for v in p['variants']])
            images = str([i['src'] for i in p['images']])
            if p['status'] == 'active' and active and not images == '[]':
                name = p['title']
                price_now = to_int(p['variants'][0]['price']) / 100
                price_before = to_int(p['variants'][0]['compare_at_price']) / 100
                # price_now = price_before
                if not price_before:
                    price_before = price_now
                discount = calculate_discount(price_before, price_now)
                original_category = p['product_type']
                category = get_category('Stradivarius', name, original_category)
                original_subcategory = original_category
                subcategory = get_subcategory('Stradivarius', name, category, original_subcategory)
                defaults = {'brand': brand, 'name': name, 'description': p['body_html'], 'url': url, 'id_producto': url,
                            'price': price_now, 'national': True, 'price_before': price_before, 'discount': discount,
                            'sale': bool(discount), 'images': images, 'category': category,
                            'original_category': original_category, 'subcategory': subcategory,
                            'original_subcategory': original_subcategory, 'gender': 'm', 'active': active}
                product, created = Product.objects.update_or_create(reference=p['id'], defaults=defaults)
                if product.active:
                    post_item(product)
                self.logs += f'    + {now.hour}:{now.minute}:{now.second}  -  {name}\n'
            else:
                product = Product.objects.filter(url=url).first()
                if product:
                    delete_from_remote(url)
                    product.delete()
                    self.logs += f'    - {now.hour}:{now.minute}:{now.second}  -  {name}\n'
        self.status = 's'
        self.save()
    except Exception as e:
        self.status = 'f'
        self.save()
        raise e


@shared_task
def crawl_mango():
    brand = 'Mango'
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(TIMEZONE),
        'status': 'x',
        'logs': f'··········{datetime.now().month} - {datetime.now().day}··········\n'})[0]
    session = requests.session()
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'referer': 'https://www.shop.mango.com/',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': get_random_agent()}
    session.headers.update(headers)
    try:
        for endpoint in SETTINGS[brand]['endpoints']:
            page_num = 1
            while page_num:
                response = session.get(endpoint[1] + str(page_num))
                if response.status_code == 200:
                    response = response.json()
                    if response['lastPage'] or page_num >= 2:
                        page_num = 0
                    else:
                        page_num += 1
                    garments = response['groups'][0]['garments']
                    self.logs += f'{datetime.now().hour}:{datetime.now().minute}  -  {len(garments)} productos  -  {endpoint[0]}\n'
                    self.save()
                    for item in garments:
                        it = garments[item]
                        name = it['shortDescription']
                        original_category = response['titleh1']
                        category = get_category(brand, name, original_category)
                        # original_subcategory = category
                        subcategory = get_subcategory(brand, name, category, category)
                        all_images, all_sizes, colors = [], [], []
                        for color in it['colors']:
                            images = []
                            sizes = []
                            for image in color['images']:
                                images.append(image['img1Src'])
                            for size in color['sizes']:
                                sizes.append(size['label'] + ('(AGOTADO)' if size['stock'] == 0 else ''))
                            all_images.append(images)
                            all_sizes.append(sizes)
                            colors.append(color['iconUrl'].replace(' ', ''))
                        all_images.reverse()  # I don't know why
                        ref = it['garmentId']
                        price_before = to_int(it['price']['crossedOutPrices'][0])
                        price_now = to_int(it['price']['salePrice'])
                        discount = it['price']['discountRate']
                        url = 'https://shop.mango.com' + it['colors'][0]['linkAnchor']
                        # self.logs += url+'\n'
                        item = find_product(url, all_images)
                        active = not all([all(['(AGOTADO)' in size for size in sizes]) for sizes in all_sizes])
                        fields = {'brand': brand, 'name': name, 'reference': ref, 'description': name, 'url': url,
                                  'id_producto': url, 'price': price_now, 'price_before': price_before,
                                  'discount': discount, 'sale': bool(discount), 'sizes': all_sizes,
                                  'colors': get_colors_src(colors), 'category': category,
                                  'original_category': original_category, 'subcategory': subcategory,
                                  'original_subcategory': category, 'gender': 'm', 'active': active,
                                  'national': False}
                        item = create_or_update_item(item, fields, session, all_images=all_images)
                        # self.logs += f'    + {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {name}\n'
                        if item.active:
                            post_item(item)
                        # else:
                        #     Debug.objects.create(name='no_stock', text=item)
                        del item, it, name, original_category, category, subcategory, all_images, all_sizes, colors, color, images, sizes, ref, price_before, price_now, discount, url, active, fields
                    self.save()
                    headers = session.headers
                    # sleep(randint(30, 120) / 1)
                    session = requests.session()
                    session.headers.update(headers)
                    # del response, garments
                else:
                    page_num = 0
                    self.logs += f'{datetime.now().hour}:{datetime.now().minute}  -  {endpoint[0]} ({response.status_code})\n'
                    self.save()
            # del page_num, endpoint
        # del brand, self, session, headers
        self.status = 's'
        self.save()
        check_inactive_items(brand, self.started)
    except Exception as e:
        self.status = 'f'
        self.save()
        raise e


@shared_task
def crawl_mercedes():
    brand = 'Mercedes Campuzano'
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(TIMEZONE),
        'status': 'x',
        'logs': f'··········{datetime.now().month} - {datetime.now().day}··········\n'})[0]
    session = requests.session()
    try:
        for endpoint in SETTINGS[brand]['endpoints']:
            response = session.get(endpoint[1]).json()
            for product in response:
                try:
                    name = product['Params']['productGroupName']
                    ref = product['ItemId']
                    price_before = product['OldPrice']
                    price_now = product['Price']
                    if not price_before:
                        price_before = price_now
                    discount = calculate_discount(price_before, price_now)
                    original_subcategory = product['CategoryNames'][0].replace('-', ' ')
                    category = get_category(brand, name, original_subcategory)
                    subcategory = get_subcategory(brand, name, category, original_subcategory)
                    url = product['Url']
                    description = product['Description']
                    all_images = [[product['PictureUrl']]]
                    if 'AlternativePictureURL' in product['Params']:
                        all_images[0].append(product['Params']['AlternativePictureURL'])
                    all_sizes = [[product['Params']['Talla']]]
                    colors = [product['Params']['Color']]
                    item = find_product(url, all_images)
                    active = not all([all(['(AGOTADO)' in size for size in sizes]) for sizes in all_sizes])
                    fields = {'brand': brand, 'name': name, 'reference': ref, 'description': description, 'url': url,
                              'id_producto': url, 'price': price_now, 'price_before': price_before,
                              'discount': discount,
                              'sale': bool(discount), 'sizes': all_sizes, 'colors': get_colors_src(colors),
                              'category': category, 'original_category': original_subcategory,
                              'subcategory': subcategory,
                              'original_subcategory': original_subcategory, 'gender': 'm', 'active': active,
                              'national': False}
                    item = create_or_update_item(item, fields, session, all_images=all_images)
                    if item.active:
                        post_item(item)
                    else:
                        self.logs += f'X {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {url} (No stock)\n'
                except Exception as e:
                    self.logs += f'\nERROR\n{e}\n'
                    Debug.objects.create(name='Error in Mercedes', text=str(e))
                # self.logs += '<>' * 10 + '\n'
                self.save()
                headers = session.headers
                # sleep(randint(30, 120) / 1)
                session = requests.session()
                session.headers.update(headers)
        self.status = 's'
        self.save()
        check_inactive_items(brand, self.started)
    except Exception as e:
        self.status = 'f'
        self.save()
        raise e


@shared_task
def crawl_pull():
    brand = 'Pull & Bear'
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(TIMEZONE),
        'status': 'x',
        'logs': f'··········{datetime.now().month} - {datetime.now().day}··········\n'})[0]
    session = requests.session()
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
    page_size = 25
    try:
        for endpoint in SETTINGS[brand]['endpoints']:
            category_id = endpoint[1][endpoint[1].index('/category/') + 10: endpoint[1].rindex('/')]
            response = session.get(endpoint[1]).json()['productIds']
            self.logs += f'{datetime.now().hour}:{datetime.now().minute}  -  {len(response)} productos  -  {endpoint[0]}\n'
            self.save()
            for page in range(len(response) // page_size):
                ids = [prod_id for prod_id in response[page * page_size: (page + 1) * page_size]]
                page_endpoint = f'https://www.pullandbear.com/itxrest/3/catalog/store/25009465/20309430/productsArray?productIds={str(ids)[1:-1].replace(", ", "%2C")}&languageId=-5&categoryId={category_id}&appId=1'
                products = session.get(page_endpoint).json()['products']
                for product in products:
                    try:
                        if 'productUrl' in product:
                            name = product['name']
                            param = f'&pelement={product["bundleProductSummaries"][0]["productUrlParam"]}' \
                                if product['bundleProductSummaries'] and 'productUrlParam' in \
                                   product['bundleProductSummaries'][0] else ''
                            url = f'https://www.pullandbear.com/co/{product["productUrl"]}?cS={product["mainColorid"]}{param}'
                            if product['bundleProductSummaries']:
                                product = product['bundleProductSummaries'][0]['detail']
                            else:
                                product = product['detail']
                            description = product['description'] if product['description'] else product[
                                'longDescription']
                            ref = product['displayReference']
                            original_category = product['familyInfo']['familyName']
                            category = get_category(brand, name, original_category)
                            original_subcategory = product['subfamilyInfo']['subFamilyName']
                            subcategory = get_subcategory(brand, name, category, original_subcategory)
                            colors, all_images, all_sizes = [], [], []
                            for color in product['colors']:
                                colors.append(
                                    f'https://static.pullandbear.net/2/photos/{color["image"]["url"]}_1_1_8.jpg?t={color["image"]["timestamp"]}&imwidth=90')
                                sizes = []
                                for size in color['sizes']:
                                    stock = '' if size['visibilityValue'] == 'SHOW' else '(AGOTADO)'
                                    sizes.append(size['name'] + stock)
                                all_sizes.append(sizes)
                            if product['xmedia']:
                                price_now = int(product['colors'][0]['sizes'][0]['price']) / 100
                                try:
                                    price_before = int(product['colors'][0]['sizes'][0]['oldPrice']) / 100
                                except TypeError:
                                    price_before = price_now
                                discount = calculate_discount(price_before, price_now)
                                for media in product['xmedia']:
                                    images = []
                                    for i in media['xmediaItems'][0]['medias']:
                                        if '_3_1_' not in i['idMedia']:
                                            images.append(
                                                f'https://static.pullandbear.net/2/photos/{media["path"]}/{i["idMedia"]}8.jpg?ts={i["timestamp"]}')
                                    all_images.append(images)
                                item = find_product(url, all_images)
                                active = not all([all(['(AGOTADO)' in size for size in sizes]) for sizes in all_sizes])
                                fields = {'brand': brand, 'name': name, 'reference': ref, 'description': name,
                                          'url': url,
                                          'id_producto': url, 'price': price_now, 'price_before': price_before,
                                          'discount': discount, 'sale': bool(discount), 'sizes': all_sizes,
                                          'colors': get_colors_src(colors), 'category': category,
                                          'original_category': original_category, 'subcategory': subcategory,
                                          'original_subcategory': original_subcategory, 'gender': 'm', 'active': active,
                                          'national': False}
                                item = create_or_update_item(item, fields, session, all_images=all_images)
                                self.logs += f'    + {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {name}\n'
                                if item.active:
                                    post_item(item)
                                    # Debug.objects.create(name='Post it', text=item.url)
                                    # pass
                                else:
                                    Debug.objects.create(name='no_stock', text=item.url)
                    except Exception as e:
                        self.logs += f'\nERROR\n{e}\n'
                        Debug.objects.create(name='Error in Pull', text=str(e))
                # self.logs += '<>' * 10 + '\n'
                # self.save()
                headers = session.headers
                sleep(randint(30, 120) / 1)
                session = requests.session()
                session.headers.update(headers)
        self.status = 's'
        self.save()
        check_inactive_items(brand, self.started)
    except Exception as e:
        self.status = 'f'
        self.save()
        raise e


@shared_task
def crawl_solua():
    session = requests.session()
    session.headers = {'X-Shopify-Access-Token': os.environ.get('SHOPIFY_SOLUA')}
    url = 'https://solua-accesorios.myshopify.com/admin/api/2021-10/products.json?limit=250&fields=id,title,variants,' \
          'images,product_type,body_html,status,handle'
    products = session.get(url).json()['products']
    brand = 'Solúa'
    now = datetime.now()
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(TIMEZONE),
        'status': 'x',
        'logs': f'··········{now.month} - {now.day}··········\n{len(products)} productos\n'})[0]
    try:
        for p in products:
            now = datetime.now()
            url = f'https://soluaccesorios.com/products/{p["handle"]}'
            if p['status'] == 'active':
                name = p['title']
                price_now = to_int(p['variants'][0]['price']) / 100
                price_before = to_int(p['variants'][0]['compare_at_price']) / 100
                if not price_before:
                    price_before = price_now
                discount = calculate_discount(price_before, price_now)
                images = str([i['src'] for i in p['images']])
                original_category = p['product_type']
                category = get_category('Stradivarius', name, original_category)
                original_subcategory = original_category
                subcategory = get_subcategory('Stradivarius', name, category, original_subcategory)
                defaults = {'brand': brand, 'name': name, 'description': p['body_html'], 'url': url, 'id_producto': url,
                            'price': price_now, 'national': True, 'price_before': price_before, 'discount': discount,
                            'sale': bool(discount), 'images': images, 'category': category,
                            'original_category': original_category, 'subcategory': subcategory,
                            'original_subcategory': original_subcategory, 'gender': 'm',
                            'active': p['status'] == 'active'}
                product, created = Product.objects.update_or_create(reference=p['id'], defaults=defaults)
                if product.active:
                    post_item(product)
                self.logs += f'    + {now.hour}:{now.minute}:{now.second}  -  {name}\n'
            elif p['status'] == 'archived':
                product = Product.objects.filter(url=url).first()
                if product:
                    delete_from_remote(url)
                    product.delete()
                    self.logs += f'    - {now.hour}:{now.minute}:{now.second}  -  {name}\n'
        self.status = 's'
        self.save()
        check_inactive_items(brand, self.started)
    except Exception as e:
        self.status = 'f'
        self.save()
        raise e


@shared_task
def crawl_stradivarius():
    brand = 'Stradivarius'
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(TIMEZONE),
        'status': 'x',
        'logs': f'··········{datetime.now().month} - {datetime.now().day}··········\n'})[0]
    session = requests.session()
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
    try:
        for endpoint in SETTINGS[brand]['endpoints']:
            products = session.get(endpoint[1]).json()['products']
            self.logs += f'{datetime.now().hour}:{datetime.now().minute}  -  {len(products)} productos  -  {endpoint[0]}\n'
            for product in products:
                try:
                    ref = f'{product["detail"]["displayReference"]}'
                    original_category = str(product['detail']['familyInfo']['familyName'])
                    original_subcategory = str(product['detail']['subfamilyInfo']['subFamilyName'])
                    prod_id = product['id']
                    cat_id = product['relatedCategories'][0]['id']
                    product = product['bundleProductSummaries'][0]
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
                    discount = calculate_discount(price_before, price_now)
                    url = f'{endpoint[0][:endpoint[0].index("-c")]}/{parse_url(name.replace(" ", "-"))}-c{cat_id}p{prod_id}.html'
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
                              'id_producto': url, 'price': price_now, 'price_before': price_before,
                              'discount': discount,
                              'sale': bool(discount), 'sizes': all_sizes, 'colors': get_colors_src(colors),
                              'category': category, 'original_category': original_category, 'subcategory': subcategory,
                              'original_subcategory': original_subcategory, 'gender': 'm', 'active': active,
                              'national': False}
                    item = create_or_update_item(item, fields, session, optional_images=optional_images)
                    if item.active:
                        post_item(item)
                    else:
                        self.logs += f'X {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {url} (No stock)\n'
                except Exception as e:
                    self.logs += f'X {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {e}\n'
            self.save()
            headers = session.headers
            sleep(randint(30, 120) / 1)
            session = requests.session()
            session.headers.update(headers)
        self.status = 's'
        self.save()
        check_inactive_items(brand, self.started)
    except Exception as e:
        self.status = 'f'
        self.save()
        raise e


@shared_task
def crawl_zara():
    brand = 'Zara'
    now = datetime.now()
    self = Process.objects.update_or_create(name=brand, defaults={
        'started': datetime.now(TIMEZONE),
        'status': 'x',
        'logs': f'··········{now.month} - {now.day}··········\n'})[0]
    session = requests.session()
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
    try:
        for endpoint in SETTINGS[brand]['endpoints']:
            now = datetime.now()
            res = session.get(endpoint[1])
            count = 0
            if res.status_code == 200:
                templates = res.json()['productGroups']
                if templates:
                    templates = templates[0]['elements']
                for template in templates:
                    count += len(template.get('commercialComponents', []))
            else:
                templates = []
                count = f'({res.status_code} error) 0'
            self.logs += f'{now.hour}:{now.minute}  -  {count} productos  -  {endpoint[0]}\n'
            self.save()
            for template in templates:
                for product in template.get('commercialComponents', []):
                    now = datetime.now()
                    try:
                        name = product['name']
                        if name:
                            description = product['description']
                            price_now = product['price'] / 100
                            price_before = product['oldPrice'] / 100 if 'oldPrice' in product else price_now
                            discount = calculate_discount(price_before, price_now)
                            url = f'https://www.zara.com/co/es/{product["seo"]["keyword"]}-p{product["seo"]["seoProductId"]}.html'
                            original_category = product['familyName']
                            original_subcategory = product['subfamilyName']
                            category = get_category(brand, name, original_category)
                            subcategory = get_subcategory(brand, name, category, original_subcategory)
                            product = product['detail']
                            ref = product['displayReference']
                            all_images, all_sizes, colors = [], [['']], []
                            for color in product['colors']:
                                colors.append(color['name'])
                                images, sizes = [], []
                                for image in color['xmedia']:
                                    images.append(
                                        f'https://static.zara.net/photos//{image["path"]}/w/563/{image["name"]}.jpg?ts={image["timestamp"]}')
                                all_images.append(images)
                            item = find_product(url, all_images)
                            active = not all([all(['(AGOTADO)' in size for size in sizes]) for sizes in all_sizes])
                            fields = {'brand': brand, 'name': name, 'reference': ref, 'description': description,
                                      'url': url,
                                      'id_producto': url, 'price': price_now, 'price_before': price_before,
                                      'discount': discount,
                                      'sale': bool(discount), 'sizes': all_sizes, 'colors': get_colors_src(colors),
                                      'category': category, 'original_category': original_category,
                                      'subcategory': subcategory,
                                      'original_subcategory': original_subcategory, 'gender': 'm', 'active': active,
                                      'national': False}
                            item = create_or_update_item(item, fields, session, all_images=all_images)
                            if item.active:
                                post_item(item)
                            else:
                                self.logs += f'X {now.hour}:{now.minute}:{now.second}  -  {url} (No stock)\n'
                    except Exception as e:
                        self.logs += f'X {now.hour}:{now.minute}:{now.second}  -  {e}\n'
            self.save()
            headers = session.headers
            sleep(randint(30, 120) / 1)
            # session = requests.session()
            session.headers.update(headers)
        self.status = 's'
        self.save()
        check_inactive_items(brand, self.started)
    except Exception as e:
        self.status = 'f'
        self.save()
        raise e


@shared_task
def pull_from_molova(brands=''):
    self = Process.objects.update_or_create(name='Sync', defaults={
        'started': datetime.now(),
        'status': 'x',
        'logs': f'··········{datetime.now().month} - {datetime.now().day}··········{brands}··········\n'})[0]
    session = requests.session()
    try:
        if brands:
            brands = [f'marcas/{b}' for b in brands.split(',')]
        else:
            brands = ['coleccion']
        for brand in brands:
            for last in ['Camisas y Camisetas', 'Pantalones y Jeans', 'Vestidos y Enterizos', 'Faldas y Shorts',
                         'Abrigos y Blazers', 'Ropa Deportiva', 'Zapatos', 'Bolsos', 'Accesorios']:
                for index in [0, 1]:
                    endpoint = f'{BASE_HOST}/{brand}/{index}/{last}'.replace(' ', '%20')
                    res = session.get(endpoint).json()
                    if 'items' in res:
                        self.logs += f'    {last} ({len(res["items"])}) - {"sale" if index else "col"}\n'
                        for item in res['items']:
                            for pop in ['data', 'date_time', 'id', 'createdAt', 'updatedAt']:
                                item.pop(pop)
                            fields = {'brand': item['brand'], 'name': item['name'], 'reference': item.get('ref', 'ref'),
                                      'id_producto': item['url'], 'url': item['url'],
                                      'description': item['description'], 'price': item['allPricesNow'],
                                      'price_before': item['priceBefore'], 'discount': item['discount'],
                                      'sale': bool(item['sale']), 'images': item['allImages'],
                                      'sizes': item['allSizes'],
                                      'colors': item['colors'], 'category': item['category'],
                                      'original_category': item['originalCategory'], 'subcategory': item['subcategory'],
                                      'original_subcategory': item['originalSubcategory'],
                                      'gender': 'm' if item['gender'] == 'Mujer' else 'h', 'active': True,
                                      'approved': True,
                                      'national': item['nacional'], 'trend': item['trend']}
                            try:
                                images = ast.literal_eval(fields['images'])
                            except ValueError:
                                images = []
                            product = find_product(fields['id_producto'], images)
                            create_or_update_item(product, fields, session, all_images=fields['images'], sync=True)
                            # self.logs += f'    + {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}  -  {product.name}\n'
                    else:
                        self.logs += f'X {last} - {"sale" if index else "col"}\n'
                    self.save()
        self.logs += '---------- END ----------'
        self.status = 's'
        self.save()
    except Exception as e:
        self.status = 'f'
        self.save()
        raise e
    return f'Brands {brands} updated'


@shared_task
def set_visibility(brand_id, visibility):
    visibility = str(visibility).title() == 'True'
    brand = Brand.objects.get(id=brand_id)
    products = Product.objects.filter(brand=brand)
    count = len(products)
    self = Process.objects.update_or_create(name=f'{brand.name} visibility', defaults={
        'started': datetime.now(),
        'logs': f'(Total {count}) 0 % to {visibility}'})[0]
    if visibility:
        for i, product in enumerate(products):
            posted = post_item(product)
            if posted:
                product.active = True
                product.save()
            self.logs = f'{(i + 1) / count * 100} % to {visibility}'
            self.save()
    else:
        to_delete = []
        for i, product in enumerate(products):
            to_delete.append(product.id_producto)
            product.active = False
            product.save()
            if len(to_delete) == 50:
                delete_from_remote(to_delete)
                to_delete.clear()
            self.logs = f'{(i + 1) / count * 100} % to {visibility}'
            self.save()
        delete_from_remote(to_delete)
    return f'{brand} set to {visibility}'
