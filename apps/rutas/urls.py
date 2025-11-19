#apps/rutas/urls.py
from django.urls import path
from .views import crear_ruta

urlpatterns = [
    path('crear/', crear_ruta, name='crear_ruta'),
]