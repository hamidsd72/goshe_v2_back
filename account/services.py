import re

import requests
from django.conf import settings


class OtpDeliveryError(Exception):
    """Raised when the OTP provider cannot accept or create an OTP."""


def normalize_iran_mobile(username):
    mobile = str(username).strip()
    if re.fullmatch(r"9\d{9}", mobile):
        return "0" + mobile
    if re.fullmatch(r"09\d{9}", mobile):
        return mobile
    raise ValueError("invalid mobile number")


def _extract_otp(payload):
    if not isinstance(payload, dict):
        raise OtpDeliveryError("invalid provider response")

    for key in ("code", "otp", "value", "Value"):
        value = payload.get(key)
        if value is not None and re.fullmatch(r"\d{6}", str(value)):
            return int(value)

    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_otp(data)

    raise OtpDeliveryError("provider response did not contain an OTP")


def send_auth_otp(username):
    token = settings.MELIPAYAMAK_OTP_TOKEN
    if not token:
        raise OtpDeliveryError("OTP provider is not configured")

    url = "https://console.melipayamak.com/api/send/otp/{token}".format(
        token=token
    )

    try:
        response = requests.post(
            url,
            json={"to": normalize_iran_mobile(username)},
            timeout=settings.MELIPAYAMAK_OTP_TIMEOUT,
        )
        response.raise_for_status()
        return _extract_otp(response.json())
    except (requests.RequestException, ValueError) as exc:
        raise OtpDeliveryError("OTP delivery failed") from exc
