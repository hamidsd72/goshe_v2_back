"""Isolated DB and fake credentials; never load .env or run a live provider."""
from api.dashboard_test_settings import *  # noqa: F401,F403

INSTALLED_APPS = INSTALLED_APPS + ['background_task']
ROOT_URLCONF = 'api.reservation_test_urls'
TIME_ZONE = 'Asia/Tehran'
MELIPAYAMAK_OTP_TOKEN = 'test-only-console-token'
MELIPAYAMAK_OTP_TIMEOUT = 10

