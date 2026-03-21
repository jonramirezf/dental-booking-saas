# ============================================================
# ARCHIVO 5/8 — config/settings.py
# UBICACIÓN: config/settings.py   REEMPLAZAR COMPLETO
# NUEVO: EMAIL_BACKEND SMTP Gmail via .env, timezone Chile,
#        TEMPLATES busca carpeta raíz 'templates/'
# ============================================================
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-cambia-esto-en-produccion'
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS', 'localhost,127.0.0.1'
).split(',')

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dentistas',
    'agenda',
    'ia',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # para templates/emails/
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── ZONA HORARIA ─────────────────────────────────────────────
LANGUAGE_CODE = 'es-cl'
TIME_ZONE     = 'America/Santiago'
USE_I18N      = True
USE_TZ        = True

# ── ARCHIVOS ESTÁTICOS Y MEDIA ───────────────────────────────
STATIC_URL      = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'agenda' / 'static']
STATIC_ROOT     = BASE_DIR / 'staticfiles'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── EMAIL ────────────────────────────────────────────────────
# Para desarrollo deja EMAIL_BACKEND vacío (usa consola)
# Para producción pon en .env:
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST=smtp.gmail.com
#   EMAIL_PORT=587
#   EMAIL_HOST_USER=tuemail@gmail.com
#   EMAIL_HOST_PASSWORD=tu_app_password_de_gmail
#   DEFAULT_FROM_EMAIL=tuemail@gmail.com
#
# IMPORTANTE — Gmail requiere "Contraseña de aplicación":
#   Gmail → Configuración → Seguridad → Verificación en 2 pasos → Contraseñas de app
#   Genera una para "Correo / Windows" → usa esa como EMAIL_HOST_PASSWORD

EMAIL_BACKEND      = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'   # dev: imprime en terminal
)
EMAIL_HOST         = os.environ.get('EMAIL_HOST',     'smtp.gmail.com')
EMAIL_PORT         = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER    = os.environ.get('EMAIL_HOST_USER',    '')
EMAIL_HOST_PASSWORD= os.environ.get('EMAIL_HOST_PASSWORD','')
EMAIL_USE_TLS      = True
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@tuclinica.com')

# ── IA ───────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
