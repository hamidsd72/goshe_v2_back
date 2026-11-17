"""Run with --settings=api.dashboard_test_settings; no external calls."""
from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from api.models import Author
from call.models import CallLog, Number
from call.views import CallCreateViewSet, AdminCallCreateViewSet
from api.reservation_providers import create_call


class CallNumberTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="9120000001", amount=100000)
        self.consultant = get_user_model().objects.create_user(username="9120000002")
        Author.objects.create(userId=self.consultant, call_price=100)

    def create_call(self, number):
        request = APIRequestFactory().post("/call_create/", {
            "userNember": number, "userIdAuthor": self.consultant.pk,
        }, format="json")
        force_authenticate(request, self.user)
        return CallCreateViewSet.as_view()(request)

    def assert_delivery(self, number, expected, registered=True):
        if registered:
            Number.objects.create(userId=self.user, number=number, subject="Test number")
        with patch("call.views.requests.request") as provider:
            provider.return_value.json.return_value = {"Sitak_id": 123, "status_id": 1}
            response = self.create_call(number)
        self.assertEqual(response.status_code, 201, response.data)
        payload = provider.call_args.kwargs["data"]
        self.assertEqual(payload["CustomerNum"], expected)
        self.assertEqual(payload["ConsultantNum"], "0" + self.consultant.username)
        self.assertEqual(CallLog.objects.get().userId, self.user)
        if registered:
            self.assertEqual(Number.objects.get().number, number)

    def test_registered_tehran_landline_uses_local_number_without_zero(self):
        self.assert_delivery("2112345678", "12345678")

    def test_registered_mobile_keeps_leading_zero(self):
        self.assert_delivery("9130000001", "09130000001")

    def test_other_city_prefix_is_unchanged(self):
        self.assert_delivery("3112345678", "03112345678")

    def test_primary_login_mobile_is_unchanged(self):
        self.assert_delivery(self.user.username, "0" + self.user.username, registered=False)

    def test_other_users_landline_cannot_be_used(self):
        Number.objects.create(userId=self.consultant, number="2112345678", subject="Other")
        with patch("call.views.requests.request") as provider:
            response = self.create_call("2112345678")
        self.assertEqual(response.status_code, 400)
        provider.assert_not_called()
        self.user.refresh_from_db()
        self.assertEqual(self.user.amount, 100000)
        self.assertFalse(CallLog.objects.exists())

    def test_stripped_landline_cannot_bypass_full_number_ownership_check(self):
        Number.objects.create(userId=self.user, number="2112345678", subject="Home")
        with patch("call.views.requests.request") as provider:
            response = self.create_call("12345678")
        self.assertEqual(response.status_code, 400)
        provider.assert_not_called()

    def test_reserved_and_immediate_calls_share_existing_endpoint_and_authorization(self):
        credit = SimpleNamespace(visit=SimpleNamespace(number=self.user.username),
            consultant_number=self.consultant.username, amount_rial=30000, rate_rial=1000)
        with patch('call.views.requests.request') as provider:
            provider.return_value.json.return_value = {'Sitak_id': 123, 'status_id': 1}
            self.assertEqual(self.create_call(self.user.username).status_code, 201)
            immediate = provider.call_args
            self.assertEqual(create_call(SimpleNamespace(pk=77), credit), 123)
            reserved = provider.call_args
        # Do not let assertion failures print any existing transport credentials.
        self.assertTrue(immediate.args == reserved.args, 'Both paths must use the same HTTP method and URL')
        self.assertTrue(immediate.kwargs['headers'] == reserved.kwargs['headers'], 'Both paths must use identical provider headers')
        self.assertEqual(reserved.kwargs['data']['Credit'], '30000')
        self.assertEqual(reserved.kwargs['data']['AmountPerMin'], '1000')
        self.assertEqual(reserved.kwargs['timeout'], 20)

    def test_admin_call_preserves_existing_payload_with_shared_transport(self):
        self.user.is_superuser = True
        request = APIRequestFactory().post('/admin-call/', {'myMobile': self.user.username,
            'username': self.consultant.username}, format='json')
        force_authenticate(request, self.user)
        with patch('call.views.requests.request') as provider:
            provider.return_value.json.return_value = {'Sitak_id': 123, 'status_id': 1}
            response = AdminCallCreateViewSet.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(provider.call_args.kwargs['data'], {'call_id': '1', 'CustomerNum': '0' + self.user.username,
            'ConsultantNum': '0' + self.consultant.username, 'Credit': '10000', 'AmountPerMin': '10'})
