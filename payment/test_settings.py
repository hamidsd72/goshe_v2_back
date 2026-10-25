"""Isolated tests: no .env, production database or real credentials.

Run: python manage.py test payment --settings=payment.test_settings
"""
SECRET_KEY = "payment-tests-only"
DEBUG = False
USE_TZ = True
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "rest_framework.authtoken",
    "account", "api", "payment",
]
MIGRATION_MODULES = {"account": None, "api": None}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "account.User"
ROOT_URLCONF = "payment.test_urls"
ALLOWED_HOSTS = ["testserver"]
MIDDLEWARE = []
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
PAYSTAR_GATEWAY_ID = "test-gateway"
PAYSTAR_SIGN_KEY = "test-signing-key"
PAYSTAR_CALLBACK_URL = "https://app.example.com/payment/result"
PAYMENT_FRONTEND_URL = "https://app.example.com"
PAYSTAR_TIMEOUT = 20
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
}
