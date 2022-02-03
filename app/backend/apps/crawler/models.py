from django.db import models
from ..utils.constants import PROCESS_STATUS
from ..utils.models import ModelBase


class Debug(ModelBase):
    name = models.CharField(max_length=30)
    text = models.TextField()

    def __str__(self):
        return self.name


class Process(ModelBase):
    name = models.CharField(max_length=30)
    started = models.DateTimeField()
    status = models.CharField(max_length=1, choices=PROCESS_STATUS, default='n')
    logs = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Proceso'
        verbose_name_plural = 'Procesos'


# class Settings(ModelBase):
#     crawl_speed = models.PositiveSmallIntegerField(default=1)
