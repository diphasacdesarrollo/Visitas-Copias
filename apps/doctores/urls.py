from django.urls import path
from .views import crear_doctor, gestionar_medicos, ver_prescripciones_doctor

app_name = 'doctores'

urlpatterns = [
    path('nuevo-doctor/', crear_doctor, name='crear_doctor'),
    path('gestionar/', gestionar_medicos, name='gestionar_medicos'),
    path('prescripciones/<int:doctor_id>/', ver_prescripciones_doctor, name='ver_prescripciones_doctor'),
]