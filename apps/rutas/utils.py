# apps/rutas/utils.py

from .models import Ruta

def actualizar_estados_de_rutas():
    rutas = Ruta.objects.all()
    for ruta in rutas:
        ruta.actualizar_estatus()