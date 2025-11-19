# visitas_medicas/settings.py
from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# Seguridad / Entorno
# =========================
# En PROD usa SECRET_KEY desde variables de entorno (Railway → Variables)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-unsafe-key")
DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    "127.0.0.1", "localhost",
    "visitasmedicasdiphasac-production.up.railway.app",
    # Si prefieres permitir cualquier subdominio de Railway:
    # ".railway.app",
]

CSRF_TRUSTED_ORIGINS = [
    "https://visitasmedicasdiphasac-production.up.railway.app",
    # Si usas subdominios múltiples en Railway:
    # "https://*.railway.app",
]

# Detrás de proxy (Railway)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookies seguras (ajusta SAMESITE según tu caso)
# - Si NO embebes el sitio en WebViews/iframes de otro dominio → Lax (recomendado)
# - Si SÍ embebes (cross-site) → CSRF_COOKIE_SAMESITE="None"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # True bloquearía lectura JS; suele quedar False

# Vista amigable de fallo CSRF
CSRF_FAILURE_VIEW = "apps.usuarios.views.csrf_failure"

# =========================
# Django apps
# =========================
AUTH_USER_MODEL = "usuarios.Usuario"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "/"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.usuarios",
    "apps.doctores",
    "apps.asistencia",
    "apps.productos",
    "apps.rutas",
    "apps.visitas",
    "apps.ubicaciones",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.usuarios.middlewares.PasswordChangeMiddleware",
]

ROOT_URLCONF = "visitas_medicas.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "visitas_medicas.wsgi.application"

# =========================
# Base de datos (Railway)
# =========================
DATABASES = {
    "default": dj_database_url.config(default=os.environ.get("DATABASE_URL"))
}

# =========================
# Password validators
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================
# Localización
# =========================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Lima"
USE_TZ = True
USE_I18N = True
USE_L10N = True

# =========================
# Estáticos / WhiteNoise
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
CSRF_FAILURE_VIEW = 'apps.usuarios.views.csrf_failure'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"