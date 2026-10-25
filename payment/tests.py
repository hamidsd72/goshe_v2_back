import hashlib
import hmac
import json
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from api.models import Transaction
from .paystar import BASE_URL, PaystarError, create_payment, rial_amount, sign, verify_payment


def provider_response(data, status=1):
    response = Mock(status_code=200)
    response.json.return_value = {"status": status, "data": data}
    return response


@override_settings(
    PAYSTAR_GATEWAY_ID="test-gateway", PAYSTAR_SIGN_KEY="test-signing-key",
    PAYSTAR_CALLBACK_URL="https://app.example.com/payment/result", PAYSTAR_TIMEOUT=20,
)
class PaystarClientTests(SimpleTestCase):
    def test_rial_is_not_multiplied_or_divided(self):
        # 10,000 toman displayed in the UI = 100,000 stored/sent rial.
        self.assertEqual(rial_amount(100000), 100000)
        self.assertEqual(rial_amount("100000.0"), 100000)
        self.assertEqual(rial_amount(5000), 5000)
        self.assertEqual(rial_amount(500000000), 500000000)

    def test_invalid_and_out_of_range_amounts(self):
        for value in (0, -1, 4999, 500000001, "1.5", "NaN", "Infinity", None, True):
            with self.subTest(value=value), self.assertRaises(PaystarError):
                rial_amount(value)

    def test_hmac_uses_text_key_and_exact_joined_fields(self):
        expected = hmac.new(b"test-signing-key", b"100000#7#https://api.example.com/", hashlib.sha512).hexdigest()
        self.assertEqual(sign(100000, "7", "https://api.example.com/"), expected)

    @patch("payment.paystar.requests.post")
    def test_create_contract_and_fee_are_separate_from_wallet_amount(self, post):
        post.return_value = provider_response({
            "token": "test token", "ref_num": "ref-7", "order_id": "7", "payment_amount": 102000,
        })
        result = create_payment(100000, 7)
        self.assertEqual(result["paid"], 102000)
        self.assertEqual(result["link"], BASE_URL + "/payment?token=test+token")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["amount"], 100000)
        self.assertEqual(payload["callback_method"], 1)
        self.assertEqual(payload["callback"], "https://app.example.com/payment/result")
        self.assertEqual(payload["order_id"], "7")
        self.assertEqual(payload["sign"], sign(100000, "7", payload["callback"]))
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-gateway")
        self.assertFalse(post.call_args.kwargs["allow_redirects"])
        self.assertGreaterEqual(post.call_args.kwargs["timeout"], 10)

    @patch("payment.paystar.requests.post")
    def test_missing_config_and_http_callback_fail_before_network(self, post):
        for setting in ({"PAYSTAR_CALLBACK_URL": "http://api.example.com/callback"},
                        {"PAYSTAR_SIGN_KEY": ""}, {"PAYSTAR_GATEWAY_ID": ""}):
            with override_settings(**setting), self.assertRaises(PaystarError):
                create_payment(100000, 7)
        post.assert_not_called()

    @patch("payment.paystar.requests.post")
    def test_create_rejects_failed_malformed_or_mismatched_responses(self, post):
        for body in (
            None, [], {"status": -1, "message": "secret provider detail"},
            {"status": 1, "data": []}, {"status": 1, "data": {}},
            {"status": 1, "data": {"token": "t", "ref_num": "r", "order_id": "other", "payment_amount": 100000}},
            {"status": 1, "data": {"token": "t", "ref_num": "r", "order_id": "7", "payment_amount": 10000}},
        ):
            with self.subTest(body=body):
                post.return_value = Mock(status_code=200)
                post.return_value.json.return_value = body
                with self.assertRaises(PaystarError) as raised:
                    create_payment(100000, 7)
                self.assertNotIn("secret provider detail", str(raised.exception))

    @patch("payment.paystar.requests.post")
    def test_network_http_and_non_json_errors_are_sanitized(self, post):
        post.side_effect = requests.Timeout("secret")
        with self.assertRaises(PaystarError) as raised:
            create_payment(100000, 7)
        self.assertNotIn("secret", str(raised.exception))
        post.side_effect = None
        post.return_value = Mock(status_code=500)
        with self.assertRaises(PaystarError):
            create_payment(100000, 7)
        post.return_value = Mock(status_code=200)
        post.return_value.json.side_effect = ValueError("invalid json")
        with self.assertRaises(PaystarError):
            create_payment(100000, 7)

    @patch("payment.paystar.requests.post")
    def test_verify_signature_and_amount(self, post):
        post.return_value = provider_response({"price": 100000, "ref_num": "ref-7", "card_number": "6037****1234"})
        verify_payment(100000, "ref-7", "6037****1234", "track", 7, 102000)
        self.assertEqual(post.call_args.args[0], BASE_URL + "/verify")
        self.assertEqual(post.call_args.kwargs["json"], {
            "amount": 100000, "ref_num": "ref-7",
            "sign": sign(100000, "ref-7", "6037****1234", "track"),
        })

    @patch("payment.paystar.requests.post")
    def test_verify_rejects_amount_or_reference_mismatch(self, post):
        for data in (
            {"price": 10000, "ref_num": "ref-7", "card_number": "masked"},
            {"price": 100000, "ref_num": "other", "card_number": "masked"},
            {"price": 100000, "ref_num": "ref-7"},
        ):
            post.return_value = provider_response(data)
            with self.assertRaises(PaystarError):
                verify_payment(100000, "ref-7", "masked", "track", 7, 102000)

    @patch("payment.paystar.requests.post")
    def test_timeout_or_already_verified_recovers_only_via_inquiry(self, post):
        for first in (requests.Timeout(), provider_response({}, status=-6)):
            post.side_effect = [first, provider_response({
                "status": "SUCCEED", "ref_num": "ref-7", "order_id": "7",
                "payment_amount": 102000, "card_number": "masked",
            })]
            self.assertEqual(verify_payment(100000, "ref-7", "masked", "track", 7, 102000)["status"], "SUCCEED")
            self.assertEqual(post.call_args.args[0], BASE_URL + "/inquiry")

    @patch("payment.paystar.requests.post")
    def test_inquiry_rejects_wrong_state_amount_order_or_reference(self, post):
        base = {"status": "SUCCEED", "ref_num": "ref-7", "order_id": "7", "payment_amount": 102000, "card_number": "masked"}
        for key, value in (("status", "VERIFY_PENDING"), ("payment_amount", 10000), ("order_id", "8"), ("ref_num", "other")):
            post.side_effect = [provider_response({}, status=-6), provider_response(dict(base, **{key: value}))]
            with self.subTest(key=key), self.assertRaises(PaystarError):
                verify_payment(100000, "ref-7", "masked", "track", 7, 102000)


@override_settings(PAYMENT_FRONTEND_URL="https://app.example.com")
class PaystarFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="9123456789", amount=30000)
        self.payment = Transaction.objects.create(userId=self.user, amount=100000, authorLink="/dashboard")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def pending(self):
        self.payment.type = "b"
        self.payment.idPay_id = "paystar:ref-7"
        self.payment.link = BASE_URL + "/payment?token=test-token"
        self.payment.payment = json.dumps({"gateway": "paystar", "amount": 100000, "user": self.user.pk, "paid": 102000})
        self.payment.save()

    def callback(self, **changes):
        data = {"status": "1", "order_id": str(self.payment.pk), "ref_num": "ref-7", "card_number": "6037****1234", "tracking_code": "track"}
        data.update(changes)
        return self.client.get("/gateway/paystar/verify/", data)

    def confirm(self, **changes):
        data = {"status": "1", "order_id": str(self.payment.pk), "ref_num": "ref-7", "card_number": "6037****1234", "tracking_code": "track"}
        data.update(changes)
        return self.client.post("/gateway/paystar/confirm/", data, format="json")

    @patch("payment.paystar_views.verify_payment", return_value={"card_number": "masked"})
    def test_frontend_confirmation_is_public_json_and_idempotent(self, verify):
        self.pending()
        self.client.force_authenticate(None)
        for _ in range(2):
            response = self.confirm(amount=1000000, userId=9999, authorLink="//evil.example")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("Location", response)
            self.assertEqual(response.data["status"], "success")
            self.assertEqual(response.data["order_id"], self.payment.pk)
            self.assertEqual(response.data["amount"], 100000)
            self.assertEqual(response.data["authorLink"], "/dashboard")
        verify.assert_called_once()
        self.user.refresh_from_db()
        self.assertEqual(self.user.amount, 130000)

    @patch("payment.paystar_views.verify_payment")
    def test_frontend_cancelled_or_incomplete_confirmation_is_json_without_credit(self, verify):
        self.pending()
        for data in ({"status": "-98", "card_number": "", "tracking_code": ""}, {"tracking_code": ""}):
            response = self.confirm(**data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["status"], "failed")
            self.assertFalse(response.data["retryable"])
            self.assertNotIn("Location", response)
            self.assert_uncredited()
        verify.assert_not_called()

    @patch("payment.paystar_views.verify_payment", side_effect=PaystarError("unavailable"))
    def test_frontend_temporary_error_can_be_retried(self, verify):
        self.pending()
        response = self.confirm()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["status"], "error")
        self.assertTrue(response.data["retryable"])
        self.assert_uncredited()

    @patch("payment.paystar_views.verify_payment")
    def test_frontend_invalid_or_forged_callback_does_not_verify(self, verify):
        self.pending()
        for data in ({"ref_num": "forged"}, {"order_id": "99999"}):
            self.assertEqual(self.confirm(**data).status_code, 404)
        self.assertEqual(self.client.post("/gateway/paystar/confirm/", [], format="json").status_code, 400)
        self.assertEqual(self.client.get("/gateway/paystar/confirm/").status_code, 405)
        verify.assert_not_called()
        self.assert_uncredited()

    def assert_uncredited(self):
        self.user.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.user.amount, 30000)
        self.assertNotEqual(self.payment.type, "s")

    @patch("payment.paystar_views.create_payment")
    def test_create_and_repeat_return_same_link_without_charging(self, create):
        create.return_value = {"ref_num": "ref-7", "paid": 102000, "link": BASE_URL + "/payment?token=test"}
        for _ in range(2):
            response = self.client.post("/gateway/paystar/create/link/", {"order_id": self.payment.pk})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {"link": create.return_value["link"]})
        create.assert_called_once_with(100000, self.payment.pk)
        self.assert_uncredited()

    @patch("payment.paystar_views.create_payment")
    def test_legacy_creation_route_uses_paystar(self, create):
        create.return_value = {"ref_num": "ref-7", "paid": 100000, "link": BASE_URL + "/payment?token=test"}
        response = self.client.post("/gateway/parspal/create/link/", {"order_id": self.payment.pk})
        self.assertEqual(response.status_code, 200)
        create.assert_called_once()

    @patch("payment.paystar_views.create_payment")
    def test_creation_requires_authentication_and_ownership(self, create):
        self.client.force_authenticate(None)
        self.assertIn(self.client.post("/gateway/paystar/create/link/", {"order_id": self.payment.pk}).status_code, (401, 403))
        other = get_user_model().objects.create_user(username="other")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post("/gateway/paystar/create/link/", {"order_id": self.payment.pk}).status_code, 404)
        create.assert_not_called()

    @patch("payment.paystar_views.create_payment", side_effect=PaystarError("unavailable"))
    def test_creation_failure_leaves_invoice_unchanged(self, create):
        self.assertEqual(self.client.post("/gateway/paystar/create/link/", {"order_id": self.payment.pk}).status_code, 502)
        self.assert_uncredited()
        self.assertEqual(self.payment.type, "p")
        self.assertIsNone(self.payment.idPay_id)

    @patch("payment.paystar_views.create_payment")
    def test_creation_rejects_invalid_order_and_non_invoice_states(self, create):
        self.assertEqual(self.client.post("/gateway/paystar/create/link/", {"order_id": "invalid"}).status_code, 400)
        for state in ("s", "w", "g", "b"):
            self.payment.type = state
            self.payment.save()
            self.assertEqual(self.client.post("/gateway/paystar/create/link/", {"order_id": self.payment.pk}).status_code, 400)
        create.assert_not_called()

    @patch("payment.paystar_views.verify_payment")
    def test_public_callback_credits_exact_rial_amount_once(self, verify):
        self.pending()
        self.client.force_authenticate(None)
        verify.return_value = {"card_number": "6037****1234"}
        for _ in range(2):
            response = self.callback()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "https://app.example.com/dashboard")
        self.user.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.user.amount, 130000)
        self.assertEqual(self.payment.type, "s")
        verify.assert_called_once_with(100000, "ref-7", "6037****1234", "track", self.payment.pk, 102000)

    @patch("payment.paystar_views.verify_payment")
    def test_form_post_callback_is_supported(self, verify):
        self.pending()
        verify.return_value = {"card_number": "masked"}
        response = self.client.post("/gateway/paystar/verify/", {
            "status": "1", "order_id": str(self.payment.pk), "ref_num": "ref-7",
            "card_number": "masked", "tracking_code": "track",
        })
        self.assertEqual(response.status_code, 302)

    @patch("payment.paystar_views.verify_payment")
    def test_cancelled_or_incomplete_callback_never_credits(self, verify):
        self.pending()
        for fields in ({"status": "-98"}, {"card_number": ""}, {"tracking_code": ""}, {"order_id": "bad"}, {"ref_num": ""}):
            self.assertEqual(self.callback(**fields).status_code, 400)
            self.assert_uncredited()
        verify.assert_not_called()

    @patch("payment.paystar_views.verify_payment")
    def test_forged_order_or_reference_never_verifies(self, verify):
        self.pending()
        self.assertEqual(self.callback(ref_num="forged").status_code, 404)
        self.assertEqual(self.callback(order_id="99999").status_code, 404)
        verify.assert_not_called()
        self.assert_uncredited()

    @patch("payment.paystar_views.verify_payment")
    def test_mutated_amount_or_beneficiary_is_rejected(self, verify):
        self.pending()
        self.payment.amount = 1000000
        self.payment.save()
        self.assertEqual(self.callback().status_code, 400)
        self.assert_uncredited()
        self.payment.amount = 100000
        self.payment.userId = get_user_model().objects.create_user(username="other")
        self.payment.save()
        self.assertEqual(self.callback().status_code, 400)
        verify.assert_not_called()

    @patch("payment.paystar_views.verify_payment", side_effect=PaystarError("not verified"))
    def test_verification_failure_never_credits(self, verify):
        self.pending()
        self.assertEqual(self.callback().status_code, 502)
        self.assert_uncredited()

    @patch("payment.paystar_views.verify_payment")
    def test_missing_snapshot_or_old_provider_reference_is_rejected(self, verify):
        self.pending()
        self.payment.payment = None
        self.payment.save()
        self.assertEqual(self.callback().status_code, 400)
        self.payment.idPay_id = "ref-7"
        self.payment.save()
        self.assertEqual(self.callback().status_code, 404)
        self.assert_uncredited()
        verify.assert_not_called()

    @patch("payment.paystar_views.verify_payment", return_value={"card_number": "masked"})
    def test_local_database_error_rolls_back_wallet_and_payment(self, verify):
        self.pending()
        with patch.object(Transaction, "save", side_effect=RuntimeError("DB failure")):
            with self.assertRaises(RuntimeError):
                self.callback()
        self.assert_uncredited()
        self.assertEqual(self.payment.type, "b")

    @patch("payment.paystar_views.verify_payment", return_value={"card_number": "masked"})
    def test_redirect_cannot_leave_configured_frontend(self, verify):
        for path in ("https://evil.example/", "//evil.example/", "/\\evil.example/"):
            self.pending()
            self.payment.authorLink = path
            self.payment.save()
            self.assertEqual(self.callback().url, "https://app.example.com/dashboard")

    @patch("payment.paystar.requests.post")
    @override_settings(
        PAYSTAR_GATEWAY_ID="test-gateway", PAYSTAR_SIGN_KEY="test-signing-key",
        PAYSTAR_CALLBACK_URL="https://app.example.com/payment/result", PAYSTAR_TIMEOUT=20,
    )
    def test_full_create_and_verify_contract(self, post):
        # Mock only HTTP: exercise service, persistence, view and wallet together.
        post.side_effect = [
            provider_response({"token": "test", "ref_num": "ref-7", "order_id": str(self.payment.pk), "payment_amount": 102000}),
            provider_response({"price": 100000, "ref_num": "ref-7", "card_number": "masked"}),
        ]
        self.assertEqual(self.client.post("/gateway/paystar/create/link/", {"order_id": self.payment.pk}).status_code, 200)
        result = self.confirm()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["status"], "success")
        self.user.refresh_from_db()
        self.assertEqual(self.user.amount, 130000)
        self.assertEqual(post.call_count, 2)

    @patch("payment.paystar.requests.post")
    @override_settings(
        PAYSTAR_GATEWAY_ID="test-gateway", PAYSTAR_SIGN_KEY="test-signing-key", PAYSTAR_TIMEOUT=20,
    )
    def test_provider_success_then_local_rollback_recovers_once_on_retry(self, post):
        self.pending()
        post.side_effect = [
            provider_response({"price": 100000, "ref_num": "ref-7", "card_number": "masked"}),
            provider_response({}, status=-6),
            provider_response({"status": "SUCCEED", "ref_num": "ref-7", "order_id": str(self.payment.pk),
                               "payment_amount": 102000, "card_number": "masked", "tracking_code": "track"}),
        ]
        with patch.object(Transaction, "save", side_effect=RuntimeError("DB failure")):
            with self.assertRaises(RuntimeError):
                self.callback()
        self.assert_uncredited()
        self.assertEqual(self.callback().status_code, 302)
        self.assertEqual(self.callback().status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.amount, 130000)
        self.assertEqual(post.call_count, 3)
