from django.urls import path
from .views import crear_ruta, eliminar_ruta

app_name = 'rutas'

urlpatterns = [
    path('crear/', crear_ruta, name='crear_ruta'),
    path('eliminar/<int:ruta_id>/', eliminar_ruta, name='eliminar_ruta'),
]