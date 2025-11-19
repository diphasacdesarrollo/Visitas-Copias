# apps/usuarios/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

class TestLogin(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='visitador', password='prueba123')

    def test_login_valido(self):
        response = self.client.post(reverse('login'), {'username': 'visitador', 'password': 'prueba123'})
        self.assertEqual(response.status_code, 302)  # Redirección tras login exitoso

    def test_login_invalido(self):
        response = self.client.post(reverse('login'), {
            'username': 'visitador',
            'password': 'incorrecta'
        })
        self.assertContains(response, "Usuario o contraseña incorrectos.")
