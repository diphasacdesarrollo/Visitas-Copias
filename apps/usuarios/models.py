#apps/usuarios/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROLES = (
        ('VISITADOR', 'Visitador Médico'),
        ('SUPERVISOR', 'Supervisor'),
    )
    rol = models.CharField(max_length=20, choices=ROLES, null=True, blank=True)
    must_change_password = models.BooleanField(default=False)  # por defecto False

    def es_supervisor(self):
        return self.rol == 'SUPERVISOR'

    def es_visitador(self):
        return self.rol == 'VISITADOR'

    def save(self, *args, **kwargs):
        # Solo obliga a cambiar contraseña si NO es superuser ni staff
        if not self.pk and not self.is_superuser and not self.is_staff:
            self.must_change_password = True
        super().save(*args, **kwargs)