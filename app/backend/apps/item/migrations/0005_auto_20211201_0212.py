# Generated by Django 2.2 on 2021-12-01 02:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('item', '0004_product_trend'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='national',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='product',
            name='trend',
            field=models.BooleanField(default=False),
        ),
    ]
