# apps/usuarios/middlewares.py
from django.shortcuts import redirect
from django.urls import reverse

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # --- Rutas que deben ignorarse ---
        if request.path.startswith('/static/'):
            return self.get_response(request)

        if request.path == "/favicon.ico":
            return self.get_response(request)

        login_url = reverse("login")
        cambiar_url = reverse("cambiar_password")

        # Cuando NO está autenticado → no aplicar middleware
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Protección total para evitar anomalías con AnonymousUser en Railway
        must_change = getattr(request.user, "must_change_password", False)

        # Si debe cambiar contraseña y no está en la página correcta → redirigir
        if must_change and request.path not in [cambiar_url, login_url]:
            return redirect("cambiar_password")

        return self.get_response(request)