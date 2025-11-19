#apps/productos/forms.py
from django.contrib import admin
from .models import Producto

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'principal_activo', 'presentacion')
    search_fields = ('nombre', 'categoria', 'principal_activo')