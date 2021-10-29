from django.contrib.auth.models import User
from django.db import models

from ..utils.models import ModelBase


class Brand(ModelBase):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    prefix = models.CharField(max_length=3)
    nit = models.CharField(max_length=30)
    phone = models.CharField(max_length=15, blank=True)
    page = models.CharField(max_length=50, blank=True)
    # logo = models.FileField(blank=True, null=True)

    def __str__(self):
        return self.name
