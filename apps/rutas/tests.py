# apps/rutas/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from apps.usuarios.models import Usuario
from apps.doctores.models import Doctor
from apps.ubicaciones.models import Departamento, Provincia, Distrito
from apps.rutas.models import Ruta
from datetime import date

class GestionarRutaTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Crear datos de ubicación
        self.departamento = Departamento.objects.create(nombre='Lima')
        self.provincia = Provincia.objects.create(nombre='Lima', departamento=self.departamento)
        self.distrito = Distrito.objects.create(nombre='Miraflores', provincia=self.provincia)

        # Crear usuario visitador
        self.usuario = Usuario.objects.create_user(username='visitador1', password='1234', rol='visitador')

        # Crear doctor
        self.doctor = Doctor.objects.create(
            cmp='CMP123',
            nombre='Juan',
            apellido='Pérez',
            especialidad='Pediatría',
            direccion='Av. Siempre Viva 123',
            ubigeo=self.distrito
        )

    def test_registro_ruta_visitador(self):
        self.client.login(username='visitador1', password='1234')
        url = reverse('crear_ruta')
        data = {
            'doctor_id': self.doctor.id,
            'fecha_visita': date.today().isoformat()
        }
        response = self.client.post(url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ruta registrada exitosamente")

        ruta = Ruta.objects.first()
        self.assertIsNotNone(ruta)
        self.assertEqual(ruta.doctor, self.doctor)
        self.assertEqual(ruta.usuario, self.usuario)