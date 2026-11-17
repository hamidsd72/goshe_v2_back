"""Reservation adapters reuse the project's existing SMS and call transports."""
from django.conf import settings
from account.services import send_pattern_sms


def configured():
    return bool(getattr(settings, 'MELIPAYAMAK_OTP_TOKEN', ''))


def create_call(call, credit):
    from call.views import request_call_provider
    number = credit.visit.number
    response = request_call_provider({
        'call_id': str(call.pk),
        'CustomerNum': number[2:] if number.startswith('21') else '0' + number,
        'ConsultantNum': '0' + credit.consultant_number,
        'Credit': str(credit.amount_rial),
        'AmountPerMin': str(credit.rate_rial),
    }, timeout=20)
    response.raise_for_status()
    payload = response.json()
    # An unclear response must never trigger a second, potentially paid call.
    if not isinstance(payload, dict) or not payload.get('Sitak_id'):
        raise ValueError('ambiguous_call_response')
    provider_id = int(payload['Sitak_id'])
    if provider_id <= 0:
        raise ValueError('ambiguous_call_response')
    return provider_id


def send_pattern(number, pattern, arguments):
    return send_pattern_sms(number, pattern, arguments)
