# apps/asistencia/urls.py
from django.urls import path
from .views import registrar_asistencia

urlpatterns = [
    path('asistencia/', registrar_asistencia, name='registrar_asistencia'),
]