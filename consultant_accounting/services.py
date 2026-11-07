"""Phase-one lifetime calculations, in toman, using existing revenue rules."""


def calculate_revenue(call_rial=None, message_toman=None, deductions_toman=None):
    """Truncate each aggregate's share, matching Revenue.vue's > 1 guard.

    Stored call amounts are treated as rial; messages and type-w deductions
    are treated as toman, as in the existing consultant revenue page.
    Integer arithmetic avoids floating-point errors for large financial sums.
    """
    call_rial = call_rial or 0
    message_toman = message_toman or 0
    deductions_toman = deductions_toman or 0
    call_share = call_rial // 20 if call_rial > 20 else 0
    message_share = message_toman // 2 if message_toman > 2 else 0
    gross = call_share + message_share
    balance = gross - deductions_toman
    return {
        'currency': 'toman',
        'call_share': call_share,
        'message_share': message_share,
        'gross_earnings': gross,
        'previous_payments': deductions_toman,
        'deductions': deductions_toman,
        'tax': None,
        'tax_status': 'pending',
        'ledger_status': 'pending',
        'balance': balance,
        'payable': max(balance, 0),
        'bank_currency': 'rial',
        'bank_payable': max(balance, 0) * 10,
    }


def get_consultant_revenue(user_id):
    """Read lifetime totals by User ID, including all historical type-w rows.

    Payments and deductions are aliases of one total and are subtracted once.
    Period allocation belongs to the reporting/settlement phases.
    """
    from django.db.models import Sum
    from api.models import Message, Transaction
    from call.models import CallLog

    call_rial = CallLog.objects.filter(authorId=user_id).aggregate(
        total=Sum('call_amount'))['total']
    message_toman = Message.objects.filter(sendTo=user_id).aggregate(
        total=Sum('amount'))['total']
    deductions_toman = Transaction.objects.filter(
        userId=user_id, type='w').aggregate(total=Sum('amount'))['total']
    return calculate_revenue(call_rial, message_toman, deductions_toman)
