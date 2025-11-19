#apps/visitas/forms.py
from django import forms
from .models import Visita, DetalleVisita
from apps.doctores.models import Doctor
from apps.productos.models import Producto

class VisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        fields = ['doctor', 'comentarios']
        widgets = {
            'comentarios': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Comentarios opcionales'}),
        }

class DetalleVisitaForm(forms.ModelForm):
    class Meta:
        model = DetalleVisita
        fields = ['producto', 'cantidad']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'min': 1}),
        }