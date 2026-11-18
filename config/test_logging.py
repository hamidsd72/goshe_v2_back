import io
import json
import logging
from pathlib import Path
import tempfile
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from log_viewer import settings as viewer_settings
from config.project_logging import PrivateLogHandler, SafeFormatter, logging_config
from config import logging_test_settings as test_settings


@override_settings(
    ROOT_URLCONF='config.logging_test_urls',
    INSTALLED_APPS=test_settings.INSTALLED_APPS,
    MIDDLEWARE=test_settings.MIDDLEWARE,
    TEMPLATES=test_settings.TEMPLATES,
    REST_FRAMEWORK=test_settings.REST_FRAMEWORK,
    STATIC_URL='/static/',
)
class ProjectLoggingTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.file = self.directory / 'project.log'
        self.handler = PrivateLogHandler(str(self.file))
        self.handler.setFormatter(SafeFormatter())
        self.addCleanup(self.handler.close)
        for name in ('project.requests', 'project.integrations', 'django.request'):
            logger = logging.getLogger(name)
            original = logger.handlers[:], logger.level, logger.propagate
            self.addCleanup(self.restore, logger, original)
            logger.handlers = [self.handler]
            logger.setLevel(logging.INFO)
            logger.propagate = False
        self.overrides = override_settings(LOG_VIEWER_FILES_DIR=str(self.directory))
        self.overrides.enable()
        self.addCleanup(self.overrides.disable)
        self.view_patch = patch.object(viewer_settings, 'LOG_VIEWER_FILES_DIR', str(self.directory))
        self.view_patch.start()
        self.addCleanup(self.view_patch.stop)
        self.client.raise_request_exception = False

    @staticmethod
    def restore(logger, original):
        logger.handlers, logger.level, logger.propagate = original

    def entries(self):
        return [json.loads(line.split('] ', 1)[1]) for line in self.file.read_text().splitlines()]

    def test_success_generates_new_request_id_and_private_metadata(self):
        response = self.client.get('/probe/ok/?token=hidden', HTTP_AUTHORIZATION='Bearer hidden',
                                   HTTP_X_REQUEST_ID='untrusted-client-id')
        self.assertEqual(response.status_code, 200)
        entry = self.entries()[-1]
        self.assertEqual(entry['request_id'], response['X-Request-ID'])
        self.assertNotEqual(entry['request_id'], 'untrusted-client-id')
        self.assertEqual(entry['route'], 'probe/ok/')
        self.assertEqual(entry['status_code'], 200)
        self.assertNotIn('hidden', self.file.read_text())

    def test_unhandled_500_keeps_stack_but_never_exception_values_or_route_parameters(self):
        response = self.client.post('/probe/crash/09123456789/?token=hidden',
                                    {'password': 'hidden', 'body': 'private consultation'})
        self.assertEqual(response.status_code, 500)
        entries = self.entries()
        self.assertTrue(any(e.get('error_type') == 'RuntimeError' for e in entries), entries)
        exception = next(e for e in entries if e.get('error_type') == 'RuntimeError')
        self.assertTrue(exception['traceback'])
        self.assertEqual(exception['request_id'], response['X-Request-ID'])
        for secret in ('09123456789', 'must-not-be-logged', 'private consultation', 'hidden'):
            self.assertNotIn(secret, self.file.read_text())
        self.assertEqual(entries[-1]['route'], 'probe/crash/<str:private>/')

    def test_handled_drf_error_is_logged_without_changing_response(self):
        response = self.client.post('/probe/error/', data='{"password":"secret"}', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': 'invalid input'})
        self.assertEqual(self.entries()[-1].get('error_type'), 'ValidationError', self.entries())
        self.assertNotIn('secret', self.file.read_text())

    def test_missing_route_is_logged_without_echoing_sensitive_path(self):
        response = self.client.get('/unknown/09123456789/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.entries()[-1]['status_code'], 404)
        self.assertNotIn('09123456789', self.file.read_text())

    def test_request_context_does_not_leak_to_background_records(self):
        self.client.get('/probe/ok/')
        logging.getLogger('project.integrations').warning('secret body', extra={'error_type': 'Timeout'})
        self.assertNotIn('request_id', self.entries()[-1])
        self.assertNotIn('secret body', self.file.read_text())

    def test_log_file_is_private_and_external_rotation_reopens_it(self):
        self.client.get('/probe/ok/')
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o600)
        old = self.file.with_name('project.log.1')
        self.file.rename(old)
        response = self.client.get('/probe/ok/')
        self.assertEqual(len(old.read_text().splitlines()), 1)
        self.assertEqual(self.entries()[0]['request_id'], response['X-Request-ID'])

    def test_disk_failure_does_not_break_request_or_dump_original_record(self):
        with patch('config.project_logging.os.open', side_effect=PermissionError('secret-path')), \
                patch('config.project_logging.sys.stderr', new_callable=io.StringIO) as stderr:
            response = self.client.get('/probe/ok/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('secret-path', stderr.getvalue())
        self.assertIn('unavailable', stderr.getvalue())

    def login(self, **flags):
        user = get_user_model().objects.create_user(username=str(get_user_model().objects.count()), **flags)
        self.client.force_login(user)
        return user

    def test_viewer_requires_active_superuser_including_downloads_and_json(self):
        urls = ['/admin/project-logs/', '/admin/project-logs/json/project.log',
                '/admin/project-logs/download/single-file/?file_name=project.log',
                '/admin/project-logs/download.zip']
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.login(is_staff=True)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_superuser_sees_admin_link_viewer_json_and_downloads(self):
        self.login(is_staff=True, is_superuser=True)
        self.client.get('/probe/ok/')
        self.assertContains(self.client.get('/admin/'), '/admin/project-logs/')
        self.assertEqual(self.client.get('/admin/project-logs/').status_code, 200)
        response = self.client.get('/admin/project-logs/json/project.log')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['logs'])
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.get('/admin/project-logs/download/single-file/?file_name=project.log').status_code, 200)
        self.assertEqual(self.client.get('/admin/project-logs/download.zip').status_code, 200)

    def test_viewer_rejects_other_files_traversal_and_symlinks(self):
        self.login(is_staff=True, is_superuser=True)
        (self.directory / '.env').write_text('do-not-read')
        self.assertEqual(self.client.get('/admin/project-logs/json/.env').status_code, 404)
        self.assertEqual(self.client.get('/admin/project-logs/download/single-file/?file_name=../.env').status_code, 404)
        link = self.directory / 'project.log.1'
        link.symlink_to(self.directory / '.env')
        self.assertEqual(self.client.get('/admin/project-logs/json/project.log.1').status_code, 404)
        self.assertEqual(self.client.get('/admin/project-logs/download.zip').status_code, 404)

    def test_config_keeps_both_file_and_console_and_no_email_traceback_handler(self):
        config = logging_config(self.directory)
        self.assertEqual(config['handlers']['project_file']['class'], 'config.project_logging.PrivateLogHandler')
        self.assertFalse(config['loggers']['django']['propagate'])

    def test_parallel_requests_have_isolated_request_ids(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.http import HttpResponse
        from django.test import RequestFactory
        from config.project_logging import RequestLogMiddleware
        barrier = Barrier(2)
        def view(request):
            barrier.wait(timeout=5)
            logging.getLogger('project.integrations').warning('transport failed')
            return HttpResponse('ok')
        middleware = RequestLogMiddleware(view)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: middleware(RequestFactory().get('/probe/ok/')), range(2)))
        ids = {r['X-Request-ID'] for r in responses}
        self.assertEqual(len(ids), 2)
        for request_id in ids:
            self.assertEqual(sum(e.get('request_id') == request_id for e in self.entries()), 2)

    def test_static_assets_are_available_locally(self):
        from django.contrib.staticfiles.finders import find
        self.assertTrue(find('log_viewer/js/jquery.min.js'))
        self.assertTrue(find('log_viewer/css/log-viewer.css'))

    def test_caught_provider_rejection_has_safe_event_and_exception_without_payload(self):
        from account.services import send_auth_otp, OtpDeliveryError
        with patch('account.services.requests.post') as http:
            http.return_value.json.return_value = {'status': 'private secret provider error'}
            with self.assertRaises(OtpDeliveryError):
                send_auth_otp('9120000001')
        entry = self.entries()[-1]
        self.assertEqual(entry['event'], 'otp_delivery_failed')
        self.assertEqual(entry['error_type'], 'OtpDeliveryError')
        self.assertTrue(entry['traceback'])
        for value in ('private secret provider error', '9120000001', 'test-only-console-token'):
            self.assertNotIn(value, self.file.read_text())
