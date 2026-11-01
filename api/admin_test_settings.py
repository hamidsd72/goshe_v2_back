"""Admin regression tests, using only the isolated in-memory test database."""
from api.dashboard_test_settings import *  # noqa: F401,F403

INSTALLED_APPS = INSTALLED_APPS + [
    "django.contrib.admin.apps.SimpleAdminConfig",
    "django.contrib.sessions",
    "django.contrib.messages",
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
