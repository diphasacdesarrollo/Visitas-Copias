#apps/doctores/admin.py
from django.contrib import admin
from .models import Doctor

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('cmp', 'nombre', 'apellido', 'especialidad', 'direccion', 'mostrar_ubigeo')
    search_fields = ('cmp', )
    list_filter = ('ubigeo__provincia__departamento', 'especialidad')  # Filtro por Departamento y Especialidad

    def mostrar_ubigeo(self, obj):
        if obj.ubigeo and obj.ubigeo.provincia and obj.ubigeo.provincia.departamento:
            return f"{obj.ubigeo.provincia.departamento.nombre} - {obj.ubigeo.provincia.nombre} - {obj.ubigeo.nombre}"
        return "-"
    mostrar_ubigeo.short_description = "Ubigeo"
