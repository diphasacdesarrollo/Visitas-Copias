#apps/rutas/forms.py
from django.contrib import admin
from .models import Ruta

@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'doctor', 'fecha_visita', 'estatus')
    search_fields = ('usuario__email', 'doctor__nombre')
    list_filter = ('fecha_visita', 'estatus')