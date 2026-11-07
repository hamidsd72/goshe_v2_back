"""Isolated SQLite settings; never import production settings or .env."""
from api.dashboard_test_settings import *  # noqa: F401,F403

INSTALLED_APPS = INSTALLED_APPS + ['consultant_accounting']
ROOT_URLCONF = 'consultant_accounting.urls'
