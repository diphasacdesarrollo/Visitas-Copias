#apps/usuarios/forms.py
from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.utils.translation import gettext_lazy as _

class CustomPasswordChangeForm(SetPasswordForm):
    
    new_password1 = forms.CharField(
        label=_("Nueva contraseña"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa nueva contraseña'
        }),
    )
    new_password2 = forms.CharField(
        label=_("Confirmar nueva contraseña"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirma la nueva contraseña'
        }),
    )