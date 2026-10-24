from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import Mock, patch
from datetime import timedelta

from .services import OtpDeliveryError, _extract_otp, normalize_iran_mobile, send_auth_otp


class MobileNormalizationTests(TestCase):
    def test_adds_iranian_trunk_prefix(self):
        self.assertEqual(normalize_iran_mobile("9123456789"), "09123456789")

    def test_rejects_invalid_mobile(self):
        with self.assertRaises(ValueError):
            normalize_iran_mobile("123")


class MeliPayamakOtpServiceTests(SimpleTestCase):
    @patch("account.services.requests.post")
    def test_accepts_actual_provider_five_digit_response(self, post):
        response = Mock()
        response.json.return_value = {"code": "12345", "status": "عملیات موفق"}
        post.return_value = response

        with self.settings(
            MELIPAYAMAK_OTP_TOKEN="test-token",
            MELIPAYAMAK_OTP_TIMEOUT=4,
        ):
            self.assertEqual(send_auth_otp("9123456789"), 12345)

    def test_rejects_invalid_provider_codes(self):
        for code in ("", "1234", "1234567", "abcde", None):
            with self.subTest(code=code):
                with self.assertRaises(OtpDeliveryError):
                    _extract_otp({"code": code})

    @patch("account.services.requests.post")
    def test_sends_mobile_and_returns_provider_otp(self, post):
        response = Mock()
        response.json.return_value = {"data": {"code": "123456"}}
        response.raise_for_status.return_value = None
        post.return_value = response

        with self.settings(
            MELIPAYAMAK_OTP_TOKEN="test-token",
            MELIPAYAMAK_OTP_TIMEOUT=4,
        ):
            code = send_auth_otp("9123456789")

        self.assertEqual(code, 123456)
        post.assert_called_once_with(
            "https://console.melipayamak.com/api/send/otp/test-token",
            json={"to": "09123456789"},
            timeout=4,
        )

    def test_requires_provider_configuration(self):
        with self.settings(MELIPAYAMAK_OTP_TOKEN=""):
            with self.assertRaises(OtpDeliveryError):
                send_auth_otp("9123456789")


class AuthOtpApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = self._create_user()

    @staticmethod
    def _create_user():
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            username="9123456789",
            password="test-password",
        )

    @patch("account.views.send_auth_otp", return_value=123456)
    def test_create_code_stores_provider_otp_with_expiry(self, send_auth_otp):
        response = self.client.post(
            "/create-code/",
            {"username": self.user.username},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.code, 123456)
        self.assertGreater(self.user.timer, timezone.now())
        send_auth_otp.assert_called_once_with(self.user.username)

    @patch("account.views.send_auth_otp", side_effect=OtpDeliveryError())
    def test_create_code_does_not_replace_code_when_delivery_fails(self, _send):
        self.user.code = 654321
        self.user.save(update_fields=["code"])

        response = self.client.post(
            "/create-code/",
            {"username": self.user.username},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.user.refresh_from_db()
        self.assertEqual(self.user.code, 654321)

    def test_verification_consumes_valid_code(self):
        self.user.code = 123456
        self.user.timer = timezone.now() + timedelta(minutes=2)
        self.user.save(update_fields=["code", "timer"])

        response = self.client.post(
            "/get-code/",
            {"username": self.user.username, "code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["allow"])
        self.user.refresh_from_db()
        self.assertIsNone(self.user.code)

    def test_expired_code_is_rejected(self):
        self.user.code = 123456
        self.user.timer = timezone.now() - timedelta(seconds=1)
        self.user.save(update_fields=["code", "timer"])

        response = self.client.post(
            "/get-code/",
            {"username": self.user.username, "code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["allow"])

# Create your tests here.
