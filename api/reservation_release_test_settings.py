"""Full regression suite on the disposable local reservation MariaDB only.

Never imports config.settings or .env. Port 33317 belongs to a temporary
container with tmpfs storage; the test database is created and removed by Django.
"""
from .reservation_regression_test_settings import *  # noqa: F401,F403
from .reservation_innodb_test_settings import DATABASES  # noqa: F401

MIGRATION_MODULES = {}
