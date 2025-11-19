#apps/asistencia/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Asistencia

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha_ingreso', 'ubicacion_ingreso_link', 'fecha_salida', 'ubicacion_salida_link')
    search_fields = ('usuario__email', 'ubicacion_ingreso', 'ubicacion_salida')
    list_filter = ('fecha_ingreso', 'fecha_salida')

    def ubicacion_ingreso_link(self, obj):
        if obj.ubicacion_ingreso:
            return format_html(
                '<a href="https://www.google.com/maps?q={0}" target="_blank">{0}</a>',
                obj.ubicacion_ingreso
            )
        return "-"
    ubicacion_ingreso_link.short_description = 'Ubicación Ingreso'

    def ubicacion_salida_link(self, obj):
        if obj.ubicacion_salida:
            return format_html(
                '<a href="https://www.google.com/maps?q={0}" target="_blank">{0}</a>',
                obj.ubicacion_salida
            )
        return "-"
    ubicacion_salida_link.short_description = 'Ubicación Salida'