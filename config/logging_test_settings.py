"""Isolated logging tests; no .env, provider calls or production database."""
from pathlib import Path
import tempfile
from config.project_logging import logging_config
from api.reservation_regression_test_settings import *  # noqa: F401,F403

INSTALLED_APPS = INSTALLED_APPS + ['log_viewer', 'django.contrib.staticfiles']
ROOT_URLCONF = 'config.logging_test_urls'
STATIC_URL = '/static/'
LOGIN_URL = '/admin/login/'
MIDDLEWARE = ['config.project_logging.RequestLogMiddleware'] + MIDDLEWARE
TEMPLATES = [dict(TEMPLATES[0], DIRS=[str(Path(__file__).resolve().parent.parent / 'templates')])]
REST_FRAMEWORK = dict(REST_FRAMEWORK, EXCEPTION_HANDLER='config.project_logging.drf_exception_handler')
# Test cases explicitly attach a private temporary file handler and remove it afterwards.
_suite_logs = tempfile.TemporaryDirectory(prefix='goshe-logging-suite-')
LOGGING = logging_config(_suite_logs.name)
LOG_VIEWER_FILES_DIR = _suite_logs.name
LOG_VIEWER_FILES = ['project.log']
LOG_VIEWER_FILES_PATTERN = 'project.log*'
LOG_VIEWER_MAX_READ_LINES = 200
