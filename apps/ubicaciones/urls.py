# apps/ubicaciones/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('provincias/', views.get_provincias, name='get_provincias'),
    path('distritos/', views.get_distritos, name='get_distritos'),
]