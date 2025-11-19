#apps/visitas/admin.py
from django.contrib import admin
from .models import Visita

@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = (
        'usuario_email',
        'doctor_cmp_nombre',
        'doctor_ubigeo',
        'ubicacion_inicio',
        'fecha_inicio',
        'fecha_final',
        'duracion_minutos',
    )
    search_fields = (
        'usuario__email',
        'doctor__nombre',
        'doctor__apellido',
        'doctor__cmp',
        'comentarios',
    )
    list_filter = (
        'fecha_inicio',
        'fecha_final',
        'usuario',
        'doctor__ubigeo__provincia__departamento',
    )
    ordering = ('-fecha_inicio',)

    def usuario_email(self, obj):
        return obj.usuario.email
    usuario_email.short_description = 'Visitador'

    def doctor_cmp_nombre(self, obj):
        return f"{obj.doctor.nombre} {obj.doctor.apellido} ({obj.doctor.cmp})"
    doctor_cmp_nombre.short_description = "Doctor"

    def doctor_ubigeo(self, obj):
        ub = obj.doctor.ubigeo
        if ub:
            return f"{ub.provincia.departamento.nombre} - {ub.provincia.nombre} - {ub.nombre}"
        return "-"
    doctor_ubigeo.short_description = "Ubigeo"

    def duracion_minutos(self, obj):
        if obj.duracion:
            total = obj.duracion.total_seconds() // 60
            return f"{int(total)} min"
        return "-"
    duracion_minutos.short_description = "Duración"