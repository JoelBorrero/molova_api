import math
import os

import boto3
import numpy as np
import pandas as pd
from zipfile import ZipFile

import ast
import requests
import tinify
import urllib.parse

from ..crawler.models import Debug
from ..crawler.services import check_images_urls, delete_from_remote, parse_url, url_is_image
from ..item.models import Product
from ..user.models import Brand
from ..utils.constants import CATEGORIES, SETTINGS


def calculate_discount(price_before, price_now):
    return int(100 - price_now / price_before * 100)


def create_or_update_item(item, fields, session, optional_images='', all_images=''):
    """
    @param item: Product object or None
    @param fields: Dict with data to be updated in item
    @param session: Requests session to avoid individual requests
    @param all_images: Will be used only if images are trusted
    @param optional_images: Will be used if images could be broken links
    """
    fields['url'] = parse_url(fields['url'])
    fields['id_producto'] = parse_url(fields['id_producto'])
    if item:
        if not item.url == fields['url'] or not item.active:
            debug = Debug.objects.update_or_create(name='Broken links')[0]
            try:
                delete_from_remote(item.url)
            except Exception as e:
                debug.text += f'X - {e}'
            debug.text += item.url + '\n'
            debug.save()
        for key in fields.keys():
            exec(f'item.{key} = fields[key]')
        item.save()
    else:
        if not all_images:
            all_images = check_images_urls(optional_images, session)
        item = Product.objects.create(brand=fields['brand'], name=fields['name'], reference=fields['reference'],
                                      description=fields['description'], url=fields['url'],
                                      id_producto=fields['id_producto'], price=fields['price'],
                                      price_before=fields['price_before'], discount=fields['discount'],
                                      images=all_images, sizes=fields['sizes'], colors=fields['colors'],
                                      category=fields['category'], original_category=fields['original_category'],
                                      subcategory=fields['subcategory'], national=fields['national'],
                                      original_subcategory=fields['original_subcategory'], gender='m',
                                      active=fields['active'], sale=bool(fields['discount']),
                                      trend=fields.get('trend', False))
    return item


def find_product(url: str, images: list) -> Product or None:
    """Returns product if found, else None

    @param url: The url to search in existing products
    @param images: List of images to iterate and search inside products if prev url doesn't match
    @return: Product or None
    """
    product = Product.objects.filter(id_producto__icontains=urllib.parse.quote(url, safe=':/')).first()
    if not product:
        product = Product.objects.filter(url__contains=normalize_url(url)).first()
    if not product:
        if type(images[0]) is list:
            optional_images = images
            images = []
            for color in optional_images:
                for image in color:
                    images.append(image)
        for image in images:
            image = normalize_url(image)
            product = Product.objects.filter(images__contains=image).first()
            if product:
                break
    return product


def generate_prefix(brand):
    brand = brand.lower().replace(' ', '-')
    while len(brand) <= 4:
        brand += brand
    prefix = brand[:3]
    c1, c2, c3 = 0, 1, 2
    while Brand.objects.filter(prefix=prefix):
        prefix = f'{brand[c1]}{brand[c2]}{brand[c3]}'
        if c3 < len(brand) - 1:
            c3 += 1
        else:
            c2 += 1
            c3 = 1
    return prefix


def generate_ref(brand, index):
    return f'{brand.prefix}_{1000 + index}'


def generate_s3_url(upload_key, tinifying=False, retry=False):
    bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'bucket')
    if tinifying:
        return f'{bucket_name}/Compressed {upload_key}'
    replacements = ((' ', '+'), ('\xa0', '%C2%A0'), ('á', 'a%CC%81'), ('á', '%C2%A0'), ('ó', 'o%CC%81'),
                    ('ñ', '%E0%B8%84'), ('ข', '%E0%B8%82')) \
        if retry else ((' ', '+'), ('á', '%C3%A1'), ('á', '%C2%A0'), ('ó', '%E0%B8%82'), ('ó', 'o%CC%81'),
                       ('ú', 'u%CC%81'), ('ñ', 'n%CC%83'), ('ñ', 'n%CC%83'), ('ข', '%E0%B8%82'), ('ค', '%E0%B8%84'),
                       ('\xa0', '%C2%A0'))
    for bf, af in replacements:
        upload_key = upload_key.replace(bf, af)
    return f'https://{bucket_name}.s3.amazonaws.com/{upload_key}'


def generate_url(brand, ref='') -> str:
    return f'whatsapp_57{brand.phone}{ref}'


def get_category(brand, name, original_category):
    brands_categories = SETTINGS['brands_categories']
    brands_subcategories = SETTINGS['brands_subcategories']
    categories_exceptions = SETTINGS['categories_exceptions']
    category = ''
    categories_list = brands_categories[brand]
    subcategories_list = brands_subcategories[brand]
    name = name.lower()
    for index, c in enumerate(categories_list):
        for cat in c:
            if cat in original_category.lower():
                if index == 0:
                    # If any cardigan in shirts
                    if any(s in name for s in categories_list[4]):
                        index = 4
                elif index == 1:
                    # If any short in pants
                    if any(s in name for s in categories_list[3]):
                        index = 3
                    # If any leggin in pants
                    elif any(s in name for s in categories_list[5]):
                        index = 5
                elif index == 4:
                    if any(s in name for s in categories_list[0]):
                        index = 0
                elif index == 6:
                    # If any sock in shoes
                    if any(s in name for s in ['sock', 'socks', 'calcetines']):
                        index = 9
                elif index == 8:
                    if any(s in name for s in categories_list[7]):
                        index = 7
                category = CATEGORIES[index]
    if not category:
        for i, c in enumerate(subcategories_list):
            for cat in c:
                if any(s in cat for s in name.split(' ')) and not category and not any(
                        s in categories_exceptions[i] for s in name.split(' ')):
                    category = CATEGORIES[i]
    if not category:
        category = CATEGORIES[-1]
    return category


def get_colors_src(colors: list):
    def get_color_src(color):
        color = color.lower()
        if "blanco" in color:
            return "https://static.e-stradivarius.net/5/photos3/2020/I/0/1/p/2593/560/003/2593560003_3_1_5.jpg" \
                   "?t=1591603662373"
        elif "negro" in color:
            return "https://static.e-stradivarius.net/5/photos3/2020/I/0/1/p/2520/446/001/2520446001_3_1_5.jpg" \
                   "?t=1578650688731"
        elif any(c in color for c in ['khaki oscuro']):
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/1809/189/550/1809188550_3_1_5.jpg" \
                   "?t=1584638546032"
        elif any(c in color for c in ['crudo', 'natural']):
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/5806/616/004/5806616004_3_1_5.jpg" \
                   "?t=1606239230009"
        elif any(c in color for c in ['verde caqui', 'verdoso']):
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/2532/688/550/2532688550_3_1_5.jpg" \
                   "?t=1612276973740"
        elif any(c in color for c in ['gris claro', 'gris vigor']):
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/5800/128/201/5800128201_3_1_5.jpg" \
                   "?t=1614169933321"
        elif "marrón" in color:
            return "https://static.e-stradivarius.net/5/photos3/2020/I/0/1/p/5005/476/415/5005476415_3_1_5.jpg" \
                   "?t=1602670087866"
        elif "azul claro" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/5800/128/040/5800128040_3_1_5.jpg" \
                   "?t=1614169933139"
        elif any(c in color for c in ['camel', 'tostao']):
            return "https://static.e-stradivarius.net/5/photos3/2021/V/1/1/p/9200/770/102/02/9200770102_3_1_5.jpg" \
                   "?t=1614267634783"
        elif "rosa" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/2617/490/146/2617490146_3_1_5.jpg" \
                   "?t=1613480445018"
        elif "fucsia" in color:
            return "https://www.gef.com.co/wcsstore/CrystalCo_CAT_AS/GEF/ES-CO/Imagenes/Swatches/swatches_genericos/Rojo-3002.png"
        elif "verde claro" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/2530/151/505/2530151505_3_1_5.jpg" \
                   "?t=1611059016110"
        elif any(c in color for c in ['verde', '131']):
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/2545/860/508/2545860508_3_1_5.jpg" \
                   "?t=1612868332925"
        elif "celeste" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/2530/151/045/2530151045_3_1_5.jpg" \
                   "?t=1611052287184"
        elif "dorado" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/0783/006/300/0783006300_3_1_5.jpg" \
                   "?t=1607013413999"
        elif "lila" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/2545/860/601/2545860601_3_1_5.jpg" \
                   "?t=1612868333047"
        elif "beige" in color:
            return "https://static.e-stradivarius.net/5/photos3/2020/I/0/1/p/6540/888/430/6540888430_3_1_5.jpg" \
                   "?t=1602063024098"
        elif "gris" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/8061/294/210/8061294210_3_1_5.jpg" \
                   "?t=1613663030327"
        elif "rojo" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/5902/235/101/5902235101_3_1_5.jpg" \
                   "?t=1599738732391"
        elif "azul" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/2502/423/045/2502423045_3_1_5.jpg" \
                   "?t=1606757897269"
        elif any(c in color for c in ['amarillo', 'mostaza']):
            return "https://www.gef.com.co/wcsstore/CrystalCo_CAT_AS/2020/GEF/ES-CO/Imagenes/Swatches" \
                   "/swatches_genericos/Amarillo-11048.png"
        elif "naranja" in color:
            return "https://www.gef.com.co/wcsstore/CrystalCo_CAT_AS/2020/GEF/ES-CO/Imagenes/Swatches" \
                   "/swatches_genericos/Naranja-38836.png"
        elif "lima" in color:
            return "https://www.gef.com.co/wcsstore/CrystalCo_CAT_AS/GEF/ES-CO/Imagenes/Swatches" \
                   "/swatches_genericos/VERDE_NEON_6654.PNG"
        elif "verde" in color:
            return "https://www.gef.com.co/wcsstore/CrystalCo_CAT_AS/GEF/ES-CO/Imagenes/Swatches" \
                   "/swatches_genericos/Verde-15849.png"
        elif "az" in color:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/2512/446/010/2512446010_3_1_5.jpg" \
                   "?t=1606152337393"
        else:
            return "https://static.e-stradivarius.net/5/photos3/2021/V/0/1/p/2545/990/001/2545990001_3_1_5.jpg" \
                   "?t=1613467824691"

    return [get_color_src(color) for color in colors]


def get_subcategory(brand, name, category, original_subcategory):
    index = CATEGORIES.index(category)
    brands_subcategories = SETTINGS['brands_subcategories']
    try:
        sub = original_subcategory.lower().split(' ')
    except AttributeError:
        return category
    name = name.lower().split(' ')
    subcategories_list = brands_subcategories[brand]
    subs = subcategories_list[index] if index < 10 else ''
    if index == 0:
        if any(s in sub for s in subs[0]) and not any(s in sub for s in subs[1] + subs[2] + subs[3]):
            return 'Camisas'
        elif any(s in sub for s in subs[1]) and not any(s in sub for s in subs[2] + subs[3]):
            return 'Camisetas'
        elif any(s in sub for s in subs[2]) and not any(s in sub for s in subs[3]):
            return 'Tops'
        elif any(s in sub for s in subs[3]):
            return 'Bodies'
        elif any(s in name for s in subs[0]):
            return 'Camisas'
        elif any(s in name for s in subs[1]):
            return 'Camisetas'
        elif any(s in name for s in subs[2]):
            return 'Tops'
    elif index == 1:
        if any(s in sub for s in subs[0]) and not any(s in sub for s in subs[1]):
            return 'Pantalones'
        elif any(s in sub for s in subs[1]):
            return 'Jeans'
        elif any(s in name for s in subs[0]):
            return 'Pantalones'
        elif any(s in name for s in subs[1]):
            return 'Jeans'
    elif index == 2:
        if any(s in sub for s in subs[0]) and not any(s in sub for s in subs[1]):
            return 'Vestidos'
        elif any(s in sub for s in subs[1]):
            return 'Enterizos'
        elif any(s in name for s in subs[0]):
            return 'Vestidos'
        elif any(s in name for s in subs[1]):
            return 'Enterizos'
    elif index == 3:
        if any(s in sub for s in subs[0]) and not any(s in sub for s in subs[1]):
            return 'Faldas'
        elif any(s in sub for s in subs[1]):
            return 'Shorts'
        elif any(s in name for s in subs[0]):
            return 'Faldas'
        elif any(s in name for s in subs[1]):
            return 'Shorts'
    elif index == 4:
        if any(s in sub for s in subs[0]) and not any(s in sub for s in subs[1]):
            return 'Abrigos'
        elif any(s in sub for s in subs[1]):
            return 'Blazers'
        elif any(s in name for s in subs[0]):
            return 'Abrigos'
        elif any(s in name for s in subs[1]):
            return 'Blazers'
    elif index == 5:
        if any(s in sub for s in subs[0]) and not any(s in sub for s in subs[1] + subs[2]):
            return 'Sudaderas'
        elif any(s in sub for s in subs[1]) and not any(s in sub for s in subs[2]):
            return 'Licras'
        elif any(s in sub for s in subs[2]):
            return 'Tops'
        elif any(s in name for s in subs[0]):
            return 'Sudaderas'
        elif any(s in name for s in subs[1]):
            return 'Licras'
        elif any(s in name for s in subs[2]):
            return 'Tops'
    elif index == 6:
        if any(s in sub for s in subs[0]) and not any(
                s in sub for s in subs[1] + subs[2] + subs[3] + subs[4] + subs[5]):
            return 'Tenis'
        elif any(s in sub for s in subs[1]) and not any(s in sub for s in subs[2] + subs[3] + subs[4] + subs[5]):
            return 'Clásicos'
        elif any(s in sub for s in subs[3]) and not any(s in sub for s in subs[2] + subs[4] + subs[5]):
            return 'Baletas'
        elif any(s in sub for s in subs[5]) and not any(s in sub for s in subs[2] + subs[4]):
            return 'Botas'
        elif any(s in sub for s in subs[4]) and not any(s in sub for s in subs[2]):
            return 'Tacones'
        elif any(s in sub for s in subs[2]):
            return 'Sandalias'
        elif any(s in name for s in subs[0]):
            return 'Tenis'
        elif any(s in name for s in subs[1]):
            return 'Clásicos'
        elif any(s in name for s in subs[3]):
            return 'Baletas'
        elif any(s in name for s in subs[5]):
            return 'Botas'
        elif any(s in name for s in subs[4]):
            return 'Tacones'
        elif any(s in name for s in subs[2]):
            return 'Sandalias'
    elif index == 7:
        if any(s in sub for s in subs[0]) and not any(s in sub for s in subs[1] + subs[2] + subs[3]):
            return 'Bolsos'
        elif any(s in sub for s in subs[1]) and not any(s in sub for s in subs[2] + subs[3]):
            return 'Morrales'
        elif any(s in sub for s in subs[2]) and not any(s in sub for s in subs[3]):
            return 'Totes'
        elif any(s in sub for s in subs[3]):
            return 'Monederos'
        elif any(s in name for s in subs[0]):
            return 'Bolsos'
        elif any(s in name for s in subs[1]):
            return 'Morrales'
        elif any(s in name for s in subs[2]):
            return 'Totes'
        elif any(s in name for s in subs[3]):
            return 'Monederos'
    elif index == 8:
        if any(s in sub for s in subs[0]) and not any(s in sub for s in
                                                      subs[1] + subs[2] + subs[3] + subs[4] + subs[5] + subs[6] + subs[
                                                          7] + subs[8] + subs[9]):
            return 'Collares'
        elif any(s in sub for s in subs[1]) and not any(
                s in sub for s in subs[2] + subs[3] + subs[4] + subs[5] + subs[6] + subs[7] + subs[8] + subs[9]):
            return 'Pulseras'
        elif any(s in sub for s in subs[2]) and not any(
                s in sub for s in subs[3] + subs[4] + subs[5] + subs[6] + subs[7] + subs[8] + subs[9]):
            return 'Aretes'
        elif any(s in sub for s in subs[3]) and not any(
                s in sub for s in subs[4] + subs[5] + subs[6] + subs[7] + subs[8] + subs[9]):
            return 'Anillos'
        elif any(s in sub for s in subs[4]) and not any(
                s in sub for s in subs[5] + subs[6] + subs[7] + subs[8] + subs[9]):
            return 'Cabeza'
        elif any(s in sub for s in subs[5]) and not any(s in sub for s in subs[6] + subs[7] + subs[8] + subs[9]):
            return 'Gafas'
        elif any(s in sub for s in subs[6]) and not any(s in sub for s in subs[7] + subs[8] + subs[9]):
            return 'Cuello'
        elif any(s in sub for s in subs[7]) and not any(s in sub for s in subs[8] + subs[9]):
            return 'Interiores'
        elif any(s in sub for s in subs[8]) and not any(s in sub for s in subs[9]):
            return 'Medias'
        elif any(s in sub for s in subs[9]):
            return 'Cinturones'
        elif any(s in name for s in subs[0]):
            return 'Collares'
        elif any(s in name for s in subs[1]):
            return 'Pulseras'
        elif any(s in name for s in subs[2]):
            return 'Aretes'
        elif any(s in name for s in subs[3]):
            return 'Anillos'
        elif any(s in name for s in subs[4]):
            return 'Cabeza'
        elif any(s in name for s in subs[5]):
            return 'Gafas'
        elif any(s in name for s in subs[6]):
            return 'Cuello'
        elif any(s in name for s in subs[7]):
            return 'Interiores'
        elif any(s in name for s in subs[8]):
            return 'Medias'
        elif any(s in name for s in subs[9]):
            return 'Cinturones'
    elif index == 9:
        if any(s in sub for s in subs[0]) and not any(s in sub for s in subs[1] + subs[2] + subs[3]):
            return 'Bikini'
        elif any(s in sub for s in subs[1]) and not any(s in sub for s in subs[2] + subs[3]):
            return 'Trikini'
        elif any(s in sub for s in subs[2]) and not any(s in sub for s in subs[3]):
            return 'Bañadores'
        elif any(s in sub for s in subs[3]):
            return 'Cover Ups'
        elif any(s in sub for s in subs[0]):
            return 'Bikini'
        elif any(s in sub for s in subs[1]):
            return 'Trikini'
        elif any(s in sub for s in subs[2]):
            return 'Bañadores'
    return category


def normalize_url(url):
    """
    @param url: Url to be cropped
    @return: Url cleaned
    """
    try:
        if 'pullandbear.com' in url:
            return url[:url.index('?cS=')]
        elif any(u in url for u in ['st.mngbcn.com', 'static.bershka.net', 'static.zara.net']):
            return url[:url.index('?ts=')]
        elif any(u in url for u in ['static.e-stradivarius.net', 'static.pullandbear.net']):
            return url[:url.index('?t=')]
        elif 'mercedescampuzano.vtexassets.com' in url:
            return url[:url.index('?width=')]
        return url[:url.index('.html') + 5]
    except ValueError:
        return url


def product_from_dict(product, brand):
    if (type(product['ref']) is float or type(product['ref']) is np.float64) and math.isnan(product['ref']):
        product['ref'] = generate_ref(brand, product['index'])
    name = product['name']
    description = product['description'] if type(product['description']) is str else ''
    if type(product['url']) is str:
        url = product['url']
        id_producto = url
    else:
        url = generate_url(brand)
        id_producto = generate_url(brand, product['ref'])
        # url = id_producto
    product['price_now'] = to_int(product['price_now'])
    product['price_before'] = to_int(product['price_before'])
    if not product['price_now']:
        product['price_now'] = product['price_before']
    product['price_now'] = product['price_before']  # To hide discount
    product['discount'] = 100 - int(product['price_now'] / product['price_before'] * 100)
    category = get_category('Mango', name, product['category'])
    # subcategory = get_subcategory('Mango', name, category, product['subcategory'])
    subcategory = product['subcategory']
    colors = [str(product[f'color{c}']).title() for c in range(1, 7) if str(product[f'color{c}']) != 'nan']
    defaults = {'id_producto': id_producto, 'reference': product['ref'], 'description': description, 'url': url,
                'price': product['price_now'], 'price_before': product['price_before'], 'discount': product['discount'],
                'sale': bool(product['discount']), 'images': str(product.get('images', [])), 'sizes': '[]',
                'colors': colors, 'category': category, 'original_category': product['category'], 'national': 1,
                'subcategory': subcategory, 'original_subcategory': product['subcategory'], 'gender': 'm'}
    return Product.objects.update_or_create(brand=brand.name, name=name, defaults=defaults)


def read_from_excel(excel, user):
    brand = Brand.objects.get(id=user)
    keys = ('ref', 'name', 'description', 'price_before', 'price_now', 'category', 'subcategory', 'url', 'color1',
            'color2', 'color3', 'color4', 'color5', 'color6', 'images')
    data = pd.read_excel(excel, engine='openpyxl', sheet_name='Productos')
    data = data.dropna(how='all')
    for i in range(len(data)):
        row = data.iloc[i]
        product_data = {'index': i}
        for index, key in enumerate(keys):
            product_data[key] = row[index]
        product, created = product_from_dict(product_data, brand)


def read_s3_to_compress(start=0, end=0):
    def tinify_img(origin, path, to, output):
        """
        @param origin: 's3' or 'file'
        @param path: url/path to image
        @param to: where image should be sent, 's3' of 'file'
        @param output: output file path
        """
        tinify.key = os.environ.get('TINIFY_API_KEY_1', 'API')
        if tinify.compression_count and tinify.compression_count > 490:
            tinify.key = os.environ.get('TINIFY_API_KEY_2', 'API')
        source = tinify.from_url(path) if origin == 's3' else tinify.from_file(path)
        if to == 's3':
            return source.store(
                service='s3',
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID', 'key'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY', 'secret'),
                region=os.environ.get('AWS_S3_REGION_NAME', 'region'),
                path=output
            )
        paths = file.split('/')[:-1]
        for i in range(len(paths)):
            if not paths[i] in os.listdir('./' + '/'.join(paths[: i])):
                os.mkdir('./' + '/'.join(paths[: i + 1]))
        return source.to_file(output)

    s3 = boto3.resource('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID', 'key'),
                        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY', 'secret'))
    bucket = s3.Bucket(os.environ.get('AWS_STORAGE_BUCKET_NAME', 'bucket'))
    files = []
    for i in bucket.objects.filter(Prefix='Products Images/'):
        if not any([i.key.endswith('/'), i.key.endswith('.ini'), '/.' in i.key]):
            files.append(i.key)
    if not end or end > len(files):
        end = len(files)
    session = requests.session()
    for index, file in enumerate(files[start:end]):
        if not url_is_image(generate_s3_url('Compressed ' + file), session):
            try:
                t = tinify_img('s3', generate_s3_url(file), 's3', generate_s3_url(file, True))
                print(f'{index} - {index / len(files) * 100}% ({tinify.compression_count} calls) - {file}')
            except:
                print(file, 'error')
        else:
            print(index, file, 'exists')


def set_product_images(images, product):
    new_images = []
    for color in product.colors:
        for index in range(len(images) - len(new_images) + 1):
            for image in images:
                if f'{color.lower()}{index}' in image:
                    new_images.append(image)
    product.images = str(new_images)
    product.save()


def to_int(s):
    if type(s) is float or type(s) is np.float64 and not math.isnan(s):
        s = int(s)
    if not type(s) is int:
        stf = 0
        s = ''.join(str(s))
        for st in s:
            try:
                stf = stf * 10 + int(st)
            except ValueError:
                pass
        return stf
    else:
        return s
