# Generated by Django 2.2 on 2022-02-03 21:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0006_auto_20220203_1758'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='process',
            name='cookie',
        ),
    ]