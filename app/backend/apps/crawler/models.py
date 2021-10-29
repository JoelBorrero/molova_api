from django.db import models
from ..utils.models import ModelBase


class Debug(ModelBase):
    name = models.CharField(max_length=30)
    text = models.TextField()

    def __str__(self):
        return self.name


class Process(ModelBase):
    name = models.CharField(max_length=30)
    started = models.DateTimeField(auto_now=True)
    logs = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Proceso'
        verbose_name_plural = 'Procesos'


# class Settings(ModelBase):
#     crawl_speed = models.PositiveSmallIntegerField(default=1)
