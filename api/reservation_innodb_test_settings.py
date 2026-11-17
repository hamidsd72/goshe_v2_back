"""Disposable Docker database on loopback port 33317, never production settings."""
from .reservation_test_settings import *  # noqa: F401,F403

MIGRATION_MODULES = {}
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.mysql', 'NAME': 'goshe_reservations_qa',
    'USER': 'root', 'PASSWORD': '', 'HOST': '127.0.0.1', 'PORT': '33317',
    'TEST': {'NAME': 'test_goshe_reservations_qa'},
    'OPTIONS': {'charset': 'utf8mb4', 'init_command': "SET default_storage_engine=InnoDB, sql_mode='STRICT_TRANS_TABLES'"},
}}
