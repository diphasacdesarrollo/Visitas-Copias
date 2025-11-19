#apps/asistencia/models.py
from django.db import models
from apps.usuarios.models import Usuario

class Asistencia(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha_ingreso = models.DateTimeField(null=True, blank=True)
    ubicacion_ingreso = models.CharField(max_length=200, null=True, blank=True)
    fecha_salida = models.DateTimeField(null=True, blank=True)
    ubicacion_salida = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.usuario.email} - {self.fecha_ingreso}"