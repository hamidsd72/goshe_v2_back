from .reservation_test_settings import *  # noqa: F401,F403
from .admin_test_settings import TEMPLATES, MIDDLEWARE

INSTALLED_APPS = INSTALLED_APPS + ['django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.sessions', 'django.contrib.messages', 'consultant_accounting']
ROOT_URLCONF = 'api.reservation_regression_test_urls'
AUTH_OTP_TTL_SECONDS = 300
