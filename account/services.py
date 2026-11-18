import re
import logging

import requests
from django.conf import settings


class OtpDeliveryError(Exception):
    """Raised when the OTP provider cannot accept or create an OTP."""


class SmsDeliveryError(Exception):
    """Console pattern submission failed; never include credentials in errors."""


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
        if value is not None and re.fullmatch(r"[0-9]{5,6}", str(value)):
            return int(value)

    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_otp(data)

    raise OtpDeliveryError("provider response did not contain an OTP")


def send_auth_otp(username):
    token = settings.MELIPAYAMAK_OTP_TOKEN
    if not token:
        logging.getLogger('project.integrations').warning('otp_not_configured')
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
    except OtpDeliveryError:
        logging.getLogger('project.integrations').warning('otp_delivery_failed', exc_info=True)
        raise
    except (requests.RequestException, ValueError) as exc:
        logging.getLogger('project.integrations').warning('otp_delivery_failed', exc_info=True,
            extra={'provider_status': getattr(getattr(exc, 'response', None), 'status_code', None)})
        raise OtpDeliveryError("OTP delivery failed") from exc


def send_pattern_sms(number, pattern, arguments):
    """Use the project's Console token and shared-pattern JSON contract."""
    token = settings.MELIPAYAMAK_OTP_TOKEN
    if not token:
        logging.getLogger('project.integrations').warning('sms_not_configured')
        raise SmsDeliveryError('SMS provider is not configured')
    try:
        response = requests.post(
            'https://console.melipayamak.com/api/send/shared/{}'.format(token),
            json={'bodyId': int(pattern), 'to': normalize_iran_mobile(number),
                  'args': [str(argument) for argument in arguments]},
            timeout=settings.MELIPAYAMAK_OTP_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        receipt = str(payload.get('recId', '')) if isinstance(payload, dict) else ''
        if not re.fullmatch(r'[0-9]+', receipt) or int(receipt) <= 0:
            raise SmsDeliveryError('SMS provider did not return a receipt')
        return receipt
    except SmsDeliveryError:
        logging.getLogger('project.integrations').warning('pattern_sms_failed', exc_info=True)
        raise
    except (requests.RequestException, ValueError, TypeError) as exc:
        logging.getLogger('project.integrations').warning('pattern_sms_failed', exc_info=True,
            extra={'provider_status': getattr(getattr(exc, 'response', None), 'status_code', None)})
        raise SmsDeliveryError('SMS delivery failed') from None
