# Generated by Django 2.2 on 2021-11-25 00:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('item', '0002_product_national'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='id_producto',
            field=models.TextField(default=1),
            preserve_default=False,
        ),
    ]
