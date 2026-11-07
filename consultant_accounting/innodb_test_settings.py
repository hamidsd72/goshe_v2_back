"""Disposable local MariaDB tests on port 33316; never import production settings.

Use only with the temporary goshe_accounting_test_db container described in docs.
Its root account has no password and its data lives in tmpfs.
"""
from .test_settings import *  # noqa: F401,F403

# Validate the stored migration graph, including legacy tables, on InnoDB.
MIGRATION_MODULES = {}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'goshe_accounting_qa',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '33316',
        'TEST': {'NAME': 'test_goshe_accounting_qa'},
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET default_storage_engine=InnoDB, sql_mode='STRICT_TRANS_TABLES'",
        },
    },
}
