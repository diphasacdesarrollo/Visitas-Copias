from django.db import models
from django.utils import timezone
from apps.doctores.models import Doctor
from apps.usuarios.models import Usuario

class Ruta(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('retraso', 'Retraso'),
        ('emergencia', 'Emergencia'),
    )

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_index=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, db_index=True)
    fecha_visita = models.DateField(db_index=True)
    estatus = models.CharField(max_length=50, choices=ESTADOS, default='pendiente', db_index=True)

    # NUEVO: fecha real en la que se cubrió la ruta (si aplica)
    fecha_visita_real = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            # Evita duplicados (mismo visitador, mismo doctor, misma fecha)
            models.UniqueConstraint(
                fields=['usuario', 'doctor', 'fecha_visita'],
                name='uniq_ruta_usuario_doctor_fecha',
            )
        ]
        indexes = [
            models.Index(fields=['usuario', 'fecha_visita']),
            models.Index(fields=['doctor', 'fecha_visita']),
            models.Index(fields=['estatus', 'fecha_visita']),
        ]
        ordering = ['fecha_visita', 'doctor_id']

    def __str__(self):
        return f"{self.usuario.username} → {self.doctor.nombre} ({self.fecha_visita})"

    def actualizar_estatus(self):
        """
        - Si existe una visita finalizada enlazada a esta ruta → 'completado'
          (y fija fecha_visita_real si aún no la tiene)
        - Si la fecha ya pasó y no hay visita → 'retraso'
        - Si es hoy o futura y no hay visita → 'pendiente' (salvo 'emergencia')
        """
        from apps.visitas.models import Visita

        hoy = timezone.localdate()

        visita_final = (
            Visita.objects
            .filter(ruta=self, fecha_final__isnull=False)
            .order_by('-fecha_final')
            .first()
        )

        if visita_final:
            self.estatus = 'completado'
            if not self.fecha_visita_real:
                try:
                    self.fecha_visita_real = visita_final.fecha_final.date()
                except Exception:
                    self.fecha_visita_real = hoy
        elif self.fecha_visita < hoy:
            self.estatus = 'retraso'
        elif self.estatus != 'emergencia':
            self.estatus = 'pendiente'

        self.save(update_fields=['estatus', 'fecha_visita_real'])