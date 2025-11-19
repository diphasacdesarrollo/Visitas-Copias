# apps/ubicaciones/models.py
from django.db import models

class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Provincia(models.Model):
    nombre = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name='provincias')

    class Meta:
        unique_together = ('nombre', 'departamento')

    def __str__(self):
        return f"{self.nombre} ({self.departamento.nombre})"

class Distrito(models.Model):
    nombre = models.CharField(max_length=100)
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE, related_name='distritos')

    class Meta:
        unique_together = ('nombre', 'provincia')

    def __str__(self):
        return f"{self.nombre} ({self.provincia.nombre}, {self.provincia.departamento.nombre})"