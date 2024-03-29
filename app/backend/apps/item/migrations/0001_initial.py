# Generated by Django 2.2 on 2021-11-20 22:22

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('archived', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('brand', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=50)),
                ('reference', models.CharField(max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('url', models.TextField()),
                ('price', models.PositiveIntegerField()),
                ('price_before', models.PositiveIntegerField()),
                ('discount', models.PositiveSmallIntegerField()),
                ('sale', models.BooleanField()),
                ('images', models.TextField()),
                ('sizes', models.TextField()),
                ('colors', models.TextField()),
                ('category', models.CharField(max_length=50)),
                ('original_category', models.CharField(max_length=50)),
                ('subcategory', models.CharField(max_length=50)),
                ('original_subcategory', models.CharField(max_length=50)),
                ('gender', models.CharField(choices=[('h', 'Hombre'), ('m', 'Mujer')], max_length=1)),
                ('active', models.BooleanField(default=False)),
                ('approved', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
