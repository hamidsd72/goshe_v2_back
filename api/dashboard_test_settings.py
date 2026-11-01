"""Isolated dashboard characterization tests. Never load config.settings or .env."""
from payment.test_settings import *  # noqa: F401,F403

INSTALLED_APPS = INSTALLED_APPS + ["call"]
MIGRATION_MODULES = {**MIGRATION_MODULES, "call": None}
