import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "ordersync-insecure-local-key")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "ordersync_lab.orders.apps.OrdersConfig",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "ordersync_lab.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "ordersync_lab.wsgi.application"
ASGI_APPLICATION = "ordersync_lab.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "ordersync"),
        "USER": os.getenv("POSTGRES_USER", "ordersync"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "ordersync_local"),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5433"),
        "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "0")),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ORDERSYNC_MAX_ATTEMPTS = int(os.getenv("ORDERSYNC_MAX_ATTEMPTS", "3"))
ORDERSYNC_RETRY_DELAYS_SECONDS = tuple(
    int(value.strip())
    for value in os.getenv("ORDERSYNC_RETRY_DELAYS_SECONDS", "5,30").split(",")
    if value.strip()
)
ORDERSYNC_JOB_LOCK_TIMEOUT_SECONDS = int(os.getenv("ORDERSYNC_JOB_LOCK_TIMEOUT_SECONDS", "300"))
ORDERSYNC_WORKER_BATCH_SIZE = int(os.getenv("ORDERSYNC_WORKER_BATCH_SIZE", "10"))
ORDERSYNC_WORKER_MIN_REMAINING_MS = int(os.getenv("ORDERSYNC_WORKER_MIN_REMAINING_MS", "5000"))

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
