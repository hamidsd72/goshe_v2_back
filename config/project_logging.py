"""Privacy-first standard logging; never serialize request bodies or exceptions' values."""
import contextvars
from datetime import datetime, timezone
import logging
import json
from logging.handlers import WatchedFileHandler
import os
from pathlib import Path
import sys
import time
import traceback
from uuid import uuid4

_context = contextvars.ContextVar('project_log_context', default=None)
SAFE_EVENTS = frozenset(('otp_delivery_failed', 'otp_not_configured', 'pattern_sms_failed',
                         'sms_not_configured', 'payment_transport_failed', 'payment_failed',
                         'reservation_call_unknown'))


def request_context(request):
    match = getattr(request, 'resolver_match', None)
    user = getattr(request, 'user', None)
    try:
        user_id = getattr(user, 'pk', None)
    except Exception:
        user_id = None  # Logging must also work while the database is unavailable.
    return {
        'method': request.method,
        # The route template has placeholders instead of telephone numbers/tokens.
        'route': getattr(match, 'route', None) or '[unresolved]',
        'user_id': user_id if isinstance(user_id, int) else None,
    }


class SafeFormatter(logging.Formatter):
    def format(self, record):
        data = {
            'time': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'logger': record.name,
            # Free-form messages may contain provider URLs, SQL, OTPs or clinical text.
            'event': 'exception' if record.exc_info else 'log_record',
        }
        data.update(_context.get() or {})
        request = getattr(record, 'request', None)
        if request is not None:
            data.update(request_context(request))
            if getattr(request, 'request_id', None):
                data['request_id'] = request.request_id
        if record.name == 'project.requests':
            data['event'] = 'request_finished'
        elif record.name == 'project.integrations':
            data['event'] = record.msg if isinstance(record.msg, str) and record.msg in SAFE_EVENTS else 'integration_failed'
        for field in ('status_code', 'duration_ms', 'provider_status'):
            value = getattr(record, field, None)
            if isinstance(value, (int, float)):
                data[field] = value
        error_type = getattr(record, 'error_type', None) or getattr(request, '_project_error_type', None)
        if isinstance(error_type, str) and error_type.isidentifier():
            data['error_type'] = error_type
        if record.exc_info and record.exc_info[0]:
            data['error_type'] = record.exc_info[0].__name__
            data['traceback'] = [
                {'file': Path(frame.f_code.co_filename).name, 'line': line, 'function': frame.f_code.co_name}
                for frame, line in traceback.walk_tb(record.exc_info[2])
            ]
        return '[{}] {}'.format(record.levelname, json.dumps(data, ensure_ascii=True))


class PrivateLogHandler(WatchedFileHandler):
    """External logrotate is safe across Gunicorn/worker processes; fail without breaking requests."""
    def __init__(self, filename):
        super().__init__(filename, encoding='utf-8', delay=True)

    def emit(self, record):
        try:
            path = Path(self.baseFilename)
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            os.close(fd)
            super().emit(record)
        except (OSError, ValueError):
            # Never call logging.handleError(): it can dump the original secret-bearing record.
            sys.stderr.write('Project log file unavailable; see sanitized console logs.\n')

    def handleError(self, record):
        sys.stderr.write('Project log write failed; see sanitized console logs.\n')


def logging_config(directory):
    handlers = ['project_file', 'project_console']
    return {
        'version': 1, 'disable_existing_loggers': False,
        'formatters': {'safe': {'()': 'config.project_logging.SafeFormatter'}},
        'handlers': {
            'project_file': {'class': 'config.project_logging.PrivateLogHandler',
                             'filename': str(Path(directory) / 'project.log'), 'formatter': 'safe'},
            'project_console': {'class': 'logging.StreamHandler', 'formatter': 'safe'},
        },
        'root': {'handlers': handlers, 'level': 'INFO'},
        'loggers': {
            'django': {'handlers': handlers, 'level': 'WARNING', 'propagate': False},
            'django.request': {'handlers': handlers, 'level': 'WARNING', 'propagate': False},
            'django.server': {'handlers': handlers, 'level': 'WARNING', 'propagate': False},
        },
    }


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid4())  # Do not trust arbitrary incoming tracing headers.
        request.request_id = request_id
        token = _context.set({'request_id': request_id})
        started = time.monotonic()
        try:
            response = self.get_response(request)
            status = response.status_code
            logging.getLogger('project.requests').log(
                logging.ERROR if status >= 500 else logging.WARNING if status >= 400 else logging.INFO,
                'request_finished', extra={
                    'request': request, 'status_code': status,
                    'duration_ms': round((time.monotonic() - started) * 1000, 2),
                    'error_type': getattr(request, '_project_error_type', None),
                })
            response['X-Request-ID'] = request_id
            return response
        finally:
            _context.reset(token)


def drf_exception_handler(exc, context):
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)
    request = context.get('request')
    if request is not None:
        request._request._project_error_type = type(exc).__name__
    return response
