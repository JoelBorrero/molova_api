from django.contrib import admin

from .models import Debug, Process#, Settings


@admin.register(Debug)
class DebugAdmin(admin.ModelAdmin):
    list_display = ('name', 'text', 'created')


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'started')
    ordering = ('-started',)
    readonly_fields = ('started',)


# @admin.register(Settings)
# class SettingsAdmin(admin.ModelAdmin):
#     list_display = ('id', 'crawl_speed')
