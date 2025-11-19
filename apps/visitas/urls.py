# apps/visitas/urls.py
from django.urls import path
from . import views

app_name = 'visitas'

urlpatterns = [
    path('iniciar-visita/sin-ruta/<int:doctor_id>/', views.iniciar_visita, name='iniciar_visita_sin_ruta'),
    path('iniciar-visita/<int:ruta_id>/', views.iniciar_visita, name='iniciar_visita'),
    path('agregar-productos/', views.agregar_productos, name='agregar_productos'),
    path('gestionar-visitas/', views.gestionar_visitas_medicas, name='gestionar_visitas_medicas'),
    path('historial/', views.ver_historial, name='ver_historial'),
    path('finalizar-visita/', views.finalizar_visita, name='finalizar_visita'),
    path('cancelar-visita/', views.cancelar_visita, name='cancelar_visita'),
]