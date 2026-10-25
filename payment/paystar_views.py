import json
from collections.abc import Mapping
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.db.models import F
from django.shortcuts import redirect
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Transaction
from .paystar import PaystarError, create_payment, verify_payment


def _return_path(author_link):
    # Never redirect to an arbitrary absolute URL stored by a client.
    path = author_link or "/dashboard"
    if (not path.startswith("/") or path.startswith("//")
            or "\\" in path or any(ord(char) < 32 for char in path)
            or urlsplit(path).netloc):
        path = "/dashboard"
    return path


def _return_url(author_link):
    return settings.PAYMENT_FRONTEND_URL.rstrip("/") + _return_path(author_link)


class PaystarCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            order_id = int(str(request.data.get("order_id", "")))
        except (ValueError, TypeError):
            return Response({"msg": "شناسه تراکنش معتبر نیست"}, status=400)
        try:
            with db_transaction.atomic():
                payment = Transaction.objects.select_for_update().get(
                    pk=order_id, userId_id=request.user.pk,
                )
                if payment.type == "b" and (payment.idPay_id or "").startswith("paystar:"):
                    return Response({"link": payment.link})
                if payment.type != "p" or payment.idPay_id:
                    return Response({"msg": "وضعیت تراکنش برای پرداخت معتبر نیست"}, status=400)
                result = create_payment(payment.amount, payment.pk)
                payment.type = "b"
                payment.idPay_id = "paystar:" + result["ref_num"]
                payment.link = result["link"]
                # Snapshot amount and beneficiary without changing the DB schema.
                payment.payment = json.dumps({
                    "gateway": "paystar", "amount": payment.amount,
                    "user": payment.userId_id, "paid": result["paid"],
                })
                payment.save(update_fields=["type", "idPay_id", "link", "payment", "updated_at"])
            return Response({"link": payment.link})
        except Transaction.DoesNotExist:
            return Response({"msg": "تراکنش یافت نشد"}, status=404)
        except PaystarError as exc:
            return Response({"msg": str(exc)}, status=502)


class PaystarCallbackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return self._callback(request.query_params)

    def post(self, request):
        return self._callback(request.data)

    def _completed(self, payment):
        # Retain the old backend callback for payments already in flight.
        return redirect(_return_url(payment.authorLink))

    def _callback(self, data):
        order_id, ref_num = data.get("order_id"), data.get("ref_num")
        try:
            order_id = int(str(order_id))
        except (TypeError, ValueError):
            return Response({"msg": "اطلاعات بازگشت پرداخت معتبر نیست"}, status=400)
        if not isinstance(ref_num, str) or not ref_num:
            return Response({"msg": "شناسه پرداخت موجود نیست"}, status=400)
        try:
            with db_transaction.atomic():
                payment = Transaction.objects.select_for_update().get(
                    pk=order_id, idPay_id="paystar:" + ref_num,
                )
                if payment.type == "s":
                    return self._completed(payment)
                if payment.type != "b":
                    return Response({"msg": "وضعیت تراکنش معتبر نیست"}, status=400)
                if str(data.get("status")) != "1":
                    # No wallet credit on cancellation or unverified callbacks.
                    return Response({"msg": "پرداخت لغو شده یا تکمیل نشده است"}, status=400)
                card, tracking = data.get("card_number"), data.get("tracking_code")
                if not all(isinstance(value, str) and 0 < len(value) <= 250
                           and "#" not in value for value in (card, tracking)):
                    return Response({"msg": "اطلاعات بازگشت پرداخت کامل نیست"}, status=400)
                try:
                    snapshot = json.loads(payment.payment or "")
                    valid = (snapshot["gateway"] == "paystar"
                             and snapshot["amount"] == payment.amount
                             and snapshot["user"] == payment.userId_id)
                    paid = snapshot["paid"]
                except (ValueError, KeyError, TypeError):
                    valid = False
                if not valid:
                    return Response({"msg": "اطلاعات تراکنش تغییر کرده است؛ با پشتیبانی تماس بگیرید"}, status=400)
                verified = verify_payment(
                    payment.amount, ref_num, card, tracking, payment.pk, paid,
                )
                user_model = get_user_model()
                user = user_model.objects.select_for_update().get(pk=payment.userId_id)
                user_model.objects.filter(pk=user.pk).update(amount=F("amount") + payment.amount)
                payment.type = "s"
                payment.status = 1
                payment.track_id = str(verified.get("tracking_code") or tracking)
                payment.card_no = verified["card_number"]
                payment.save(update_fields=["type", "status", "track_id", "card_no", "updated_at"])
            return self._completed(payment)
        except Transaction.DoesNotExist:
            return Response({"msg": "تراکنش یافت نشد"}, status=404)
        except get_user_model().DoesNotExist:
            return Response({"msg": "کاربر تراکنش موجود نیست"}, status=400)
        except PaystarError as exc:
            return Response({"msg": str(exc)}, status=502)


class PaystarConfirmView(PaystarCallbackView):
    """JSON-only confirmation, called by Vue after the provider GET redirect.

    No login/session is required: provider reference + local order locate the
    payment, and only server-to-server verification can authorize wallet credit.
    """
    http_method_names = ["post", "options"]

    def post(self, request):
        if not isinstance(request.data, Mapping):
            return Response({"status": "failed", "msg": "اطلاعات پرداخت معتبر نیست", "retryable": False}, status=400)
        response = self._callback(request.data)
        if response.status_code >= 400:
            response.data["status"] = "error" if response.status_code >= 500 else "failed"
            response.data["retryable"] = response.status_code >= 500
        return response

    def _completed(self, payment):
        return Response({
            "status": "success",
            "msg": "پرداخت با موفقیت تأیید شد و موجودی افزایش یافت",
            "order_id": payment.pk,
            "amount": payment.amount,
            "tracking_code": payment.track_id,
            "authorLink": _return_path(payment.authorLink),
        })
