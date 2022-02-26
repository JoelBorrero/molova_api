from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('brand', 'name', 'sale', 'updated', 'active')
    list_filter = ('brand', 'sale', 'category', 'active')
    ordering = ('-updated', )
    readonly_fields = ('updated', 'meta')
    search_fields = ('name', )
