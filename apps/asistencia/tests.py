# apps/asistencia/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.asistencia.models import Asistencia

class IniciarJornadaIntegrationTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='visitador', password='prueba123')
        self.user.must_change_password = False  # <- DESACTIVA redirección obligatoria
        self.user.save()

    def test_flujo_completo_inicio_jornada(self):
        self.client.login(username='visitador', password='prueba123')

        response = self.client.post(reverse('registrar_asistencia'), {
            'accion': 'ingreso',
            'ubicacion': 'PruebaLat,PruebaLng'
        }, follow=True)

        self.assertContains(response, "Ingreso registrado correctamente.")
        self.assertTrue(Asistencia.objects.filter(usuario=self.user).exists())