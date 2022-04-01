# Generated by Django 2.2 on 2022-03-23 16:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('item', '0008_product_meta'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='category_b',
            field=models.CharField(choices=[('cc', 'Camisas y Camisetas'), ('pj', 'Pantalones y Jeans'), ('ve', 'Vestidos y Enterizos'), ('fs', 'Faldas y Shorts'), ('ab', 'Abrigos y Blazers'), ('rd', 'Ropa deportiva'), ('za', 'Zapatos'), ('bo', 'Bolsos'), ('ac', 'Accesorios'), ('sw', 'Swimwear'), ('ot', 'Otros')], default='ot', max_length=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='subcategory_b',
            field=models.CharField(choices=[('ca', 'Camisas'), ('cm', 'Camisetas'), ('to', 'Tops'), ('bo', 'Bodies'), ('pa', 'Pantalones'), ('je', 'Jeans'), ('ve', 'Vestidos'), ('en', 'Enterizos'), ('fa', 'Faldas'), ('sh', 'Shorts'), ('ab', 'Abrigos'), ('bl', 'Blazers'), ('su', 'Sudaderas'), ('li', 'Licras'), ('te', 'Tenis'), ('cl', 'Clásicos'), ('ba', 'Baletas'), ('bt', 'Botas'), ('ta', 'Tacones'), ('sa', 'Sandalias'), ('bs', 'Bolsos'), ('mo', 'Morrales'), ('tt', 'Totes'), ('mn', 'Monederos'), ('co', 'Collares'), ('pu', 'Pulseras'), ('ar', 'Aretes'), ('an', 'Anillos'), ('cb', 'Cabeza'), ('ga', 'Gafas'), ('cu', 'Cuello'), ('in', 'Interiores'), ('me', 'Medias'), ('ci', 'Cinturones'), ('bi', 'Bikini'), ('tr', 'Trikini'), ('bd', 'Bañadores'), ('cv', 'Cover Ups')], default='cv', max_length=2),
            preserve_default=False,
        ),
    ]