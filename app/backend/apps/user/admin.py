from django.contrib import admin

from .models import Brand


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'prefix')
    # list_filter = ('owner',)
    search_fields = ('name', 'nit')
