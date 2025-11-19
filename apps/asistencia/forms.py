#apps/asistencia/forms.py
from django import forms
from .models import Asistencia

class AsistenciaForm(forms.ModelForm):
    class Meta:
        model = Asistencia
        exclude = ['usuario']