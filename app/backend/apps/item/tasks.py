import os

import ast
import pandas as pd
from celery import shared_task

from .services import generate_s3_url, url_is_image
from ..crawler.models import Process, Debug


@shared_task
def read_to_add_images():
    def shorten(text):
        return text.replace('https://recursosmolova.s3.amazonaws.com/Compressed+Products+Images/', '')

    main_folder = './Recursos Marcas'
    for brand in [b for b in os.listdir(main_folder) if not (b.startswith('.') or b.startswith('0.'))]:
        brand_folder = f'{main_folder}/{brand}'
        excel = [f'{brand_folder}/{f}' for f in os.listdir(brand_folder) if 'Plantilla Carga' in f][0]
        data = pd.read_excel(excel, engine='openpyxl', sheet_name='Productos')
        data = data.dropna(how='all')
        keys = data.keys()[:14]
        data = data[keys]
        debug_name = brand + ' images'
        debug = Debug.objects.filter(name=debug_name).first()
        if not debug:
            debug = Debug.objects.create(name=debug_name, text='{"losen":{"compressed":[],"normal":[]},"verified":[]}')
        images_data = ast.literal_eval(debug.text)
        brand_images = []
        for i in range(len(data)):
            row = data.iloc[i]
            product_name = row[1].strip().replace("/", "-")
            images = []
            product_folder = f'{brand_folder}/{brand}/{product_name}'
            for filename in [f for f in os.listdir(product_folder)
                             if not any([f.startswith('.'), f.endswith('.ini'), '/._' in f])]:
                url = generate_s3_url(f'Compressed Products Images/{brand}/{product_name}/{filename}')
                if shorten(url) in images_data['verified']:
                    images.append(url)
                else:
                    image_exists = url_is_image(url)
                    if not image_exists:
                        image_exists = url_is_image(generate_s3_url(
                            f'Compressed Products Images/{brand}/{product_name}/{filename}', retry=True))
                        if image_exists:
                            url = generate_s3_url(f'Compressed Products Images/{brand}/{product_name}/{filename}', retry=True)
                        else:
                            images_data['losen']['compressed'].append(shorten(url))
                            url = generate_s3_url(f'Products Images/{brand}/{product_name}/{filename}')
                            image_exists = url_is_image(url)
                    if image_exists:
                        images.append(url)
                        images_data['verified'].append(shorten(url))
                    else:
                        images_data['losen']['normal'].append(shorten(url))
            debug.text = str(images_data)
            debug.save()
            brand_images.append(images)
        data['Imágenes'] = brand_images
        writer = pd.ExcelWriter(f'{main_folder}/0. Generated/{brand}.xlsx', engine='xlsxwriter')
        data.to_excel(writer, 'Productos', index=False)
        writer.save()
