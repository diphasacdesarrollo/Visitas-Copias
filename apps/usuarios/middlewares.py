#apps/usuarios/middlewares.py
from django.shortcuts import redirect
from django.urls import reverse
import logging
logger = logging.getLogger(__name__)

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            logger.debug(f"must_change_password: {getattr(request.user, 'must_change_password', 'No definido')}")
            
        if (
            request.user.is_authenticated and
            getattr(request.user, 'must_change_password', False) and
            request.path != reverse('cambiar_password') and
            not request.path.startswith('/admin/')  # ← opcional, para evitar bucle en admin
        ):
            return redirect('cambiar_password')

        return self.get_response(request)