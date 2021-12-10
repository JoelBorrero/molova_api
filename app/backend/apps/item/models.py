from django.db import models

from ..utils.constants import GENDERS
from ..utils.models import ModelBase


class Product(ModelBase):
    brand = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    reference = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    url = models.TextField()
    id_producto = models.TextField()
    price = models.PositiveIntegerField()
    price_before = models.PositiveIntegerField()
    discount = models.PositiveSmallIntegerField()
    sale = models.BooleanField()
    images = models.TextField()
    sizes = models.TextField()
    colors = models.TextField()
    category = models.CharField(max_length=50)
    original_category = models.CharField(max_length=50)
    subcategory = models.CharField(max_length=50)
    original_subcategory = models.CharField(max_length=50)
    gender = models.CharField(max_length=1, choices=GENDERS)
    active = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    national = models.BooleanField(default=False)
    trend = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
