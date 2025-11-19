#apps/productos/models.py
from django.db import models

class Producto(models.Model):
    TIPO_CHOICES = [
        ('prescribible', 'Producto Prescribible'),
        ('muestra', 'Muestra Médica'),
        ('promocional', 'Producto Promocional'),
        ('merch', 'Material Promocional / Merch'),
    ]

    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=100)
    principal_activo = models.CharField(max_length=100)
    presentacion = models.CharField(max_length=100)
    tipo_producto = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='prescribible',
    )

    def __str__(self):
        return self.nombre