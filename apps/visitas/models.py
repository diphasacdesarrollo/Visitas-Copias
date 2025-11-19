#apps/visitas/models.py
from django.db import models
from apps.usuarios.models import Usuario
from apps.doctores.models import Doctor
from apps.productos.models import Producto
from apps.rutas.models import Ruta

class Visita(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    ruta = models.ForeignKey(Ruta, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    ubicacion_inicio = models.CharField(max_length=200, blank=True, null=True)
    fecha_final = models.DateTimeField(blank=True, null=True)
    comentarios = models.TextField(blank=True, null=True)
    duracion = models.DurationField(null=True, blank=True)

    def calcular_duracion(self):
        if self.fecha_inicio and self.fecha_final:
            return self.fecha_final - self.fecha_inicio
        return None

class DetalleVisita(models.Model):
    visita = models.ForeignKey(Visita, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    tipo_entrega = models.CharField(
        max_length=20,
        choices=[
            ('muestra', 'Muestra Médica'),
            ('merch', 'Merchandising'),
        ],
        blank=True,
        null=True
    )

class ProductoPresentado(models.Model):
    visita = models.ForeignKey(Visita, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('visita', 'producto')
