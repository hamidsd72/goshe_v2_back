"""Paystar REST client. All amounts, including wallet balances, are in IRR.

Protocol: https://docs.paystar.ir/docs/gateway
Never use callback status alone as proof of payment.
"""
import hashlib
import hmac
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlsplit

import requests
from django.conf import settings


BASE_URL = "https://core.paystar.ir/api/pardakht"


class PaystarError(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def rial_amount(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount != amount.to_integral_value():
            raise ValueError
        amount = int(amount)
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        raise PaystarError("مبلغ باید عدد صحیح و به ریال باشد") from None
    if not 5000 <= amount <= 500000000:
        raise PaystarError("مبلغ باید بین ۵٬۰۰۰ و ۵۰۰٬۰۰۰٬۰۰۰ ریال باشد")
    return amount


def sign(*parts):
    if not settings.PAYSTAR_SIGN_KEY:
        raise PaystarError("تنظیمات درگاه پرداخت کامل نیست")
    return hmac.new(
        settings.PAYSTAR_SIGN_KEY.encode("utf-8"),
        "#".join(str(part) for part in parts).encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()


def _post(action, payload):
    if not settings.PAYSTAR_GATEWAY_ID:
        raise PaystarError("تنظیمات درگاه پرداخت کامل نیست")
    try:
        response = requests.post(
            BASE_URL + "/" + action,
            json=payload,
            headers={
                "Authorization": "Bearer " + settings.PAYSTAR_GATEWAY_ID,
                "Accept": "application/json",
            },
            timeout=max(10, settings.PAYSTAR_TIMEOUT),
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise PaystarError("ارتباط با درگاه پرداخت ناموفق بود")
        body = response.json()
    except (requests.RequestException, ValueError):
        # Do not expose request headers, credentials or raw provider messages.
        raise PaystarError("ارتباط با درگاه پرداخت ناموفق بود") from None
    if not isinstance(body, dict):
        raise PaystarError("پاسخ درگاه پرداخت معتبر نیست")
    if str(body.get("status")) != "1":
        raise PaystarError("درگاه پرداخت درخواست را نپذیرفت", code=body.get("status"))
    if not isinstance(body.get("data"), dict):
        raise PaystarError("پاسخ درگاه پرداخت کامل نیست")
    return body["data"]


def create_payment(amount, order_id):
    amount = rial_amount(amount)
    callback = settings.PAYSTAR_CALLBACK_URL
    parsed = urlsplit(callback)
    if parsed.scheme != "https" or not parsed.netloc or parsed.fragment or parsed.username:
        raise PaystarError("آدرس بازگشت درگاه باید HTTPS و متعلق به دامنه ثبت‌شده باشد")
    order_id = str(order_id)
    data = _post("create", {
        "amount": amount,
        "order_id": order_id,
        "callback": callback,
        "callback_method": 1,
        "sign": sign(amount, order_id, callback),
    })
    token, ref_num = data.get("token"), data.get("ref_num")
    if (not isinstance(token, str) or not token or not ref_num
            or str(data.get("order_id")) != order_id):
        raise PaystarError("شناسه تراکنش بازگشتی معتبر نیست")
    try:
        paid = Decimal(str(data["payment_amount"]))
        if not paid.is_finite() or paid < amount or paid != paid.to_integral_value():
            raise ValueError
    except (KeyError, InvalidOperation, ValueError):
        raise PaystarError("مبلغ نهایی درگاه معتبر نیست") from None
    link = BASE_URL + "/payment?" + urlencode({"token": token})
    if len(link) > 250 or len(str(ref_num)) > 240:
        raise PaystarError("شناسه تراکنش بازگشتی معتبر نیست")
    return {"ref_num": str(ref_num), "link": link, "paid": int(paid)}


def _matches(value, expected):
    try:
        return Decimal(str(value)) == Decimal(str(expected))
    except InvalidOperation:
        return False


def verify_payment(amount, ref_num, card_number, tracking_code, order_id, paid):
    amount = rial_amount(amount)
    try:
        data = _post("verify", {
            "amount": amount,
            "ref_num": ref_num,
            "sign": sign(amount, ref_num, card_number, tracking_code),
        })
    except PaystarError:
        # A previous verify may have succeeded before a timeout or DB rollback.
        # Only a server-to-server inquiry reporting SUCCEED can recover it.
        data = _post("inquiry", {"ref_num": ref_num})
        if (data.get("status") != "SUCCEED"
                or str(data.get("order_id")) != str(order_id)
                or not _matches(data.get("payment_amount"), paid)):
            raise PaystarError("پرداخت توسط درگاه تأیید نشده است")
    else:
        if not _matches(data.get("price"), amount):
            raise PaystarError("مبلغ تأییدشده با مبلغ تراکنش مطابقت ندارد")
    if str(data.get("ref_num")) != ref_num:
        raise PaystarError("شناسه پرداخت تأییدشده مطابقت ندارد")
    if (not isinstance(data.get("card_number"), str)
            or not 0 < len(data["card_number"]) <= 250
            or len(str(data.get("tracking_code", ""))) > 250):
        raise PaystarError("اطلاعات تأیید پرداخت کامل نیست")
    return data
