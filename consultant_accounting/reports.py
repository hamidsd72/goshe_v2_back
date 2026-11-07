"""Read-only period reports. Historical payments have no source allocation."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from api.models import Author, Message, Transaction
from call.models import CallLog
from .services import calculate_revenue


def date_boundary(value):
    return timezone.make_aware(datetime.combine(value, time.min), ZoneInfo('Asia/Tehran'))


def totals(queryset, owner_field, amount_field):
    return dict(queryset.values(owner_field).annotate(
        total=Sum(amount_field)).values_list(owner_field, 'total'))


def build_report(start=None, end=None, consultant=None, search=''):
    users = get_user_model().objects.filter(
        pk__in=Author.objects.exclude(userId=None).values('userId')).order_by('pk')
    if consultant:
        users = users.filter(pk=consultant)
    if search:
        users = users.filter(Q(first_name__icontains=search) |
                             Q(last_name__icontains=search) | Q(username__icontains=search))
    user_ids = list(users.values_list('pk', flat=True))
    sources = [
        (CallLog.objects.filter(authorId__in=user_ids), 'authorId', 'call_amount'),
        (Message.objects.filter(sendTo__in=user_ids), 'sendTo', 'amount'),
        (Transaction.objects.filter(userId__in=user_ids, type='w').annotate(
            event_at=Coalesce('settlement_document__batch__paid_at', 'created_at')), 'userId', 'amount'),
    ]
    before, current = [], []
    for queryset, owner, amount in sources:
        date_field = 'event_at' if owner == 'userId' else 'created_at'
        if end:
            queryset = queryset.filter(**{date_field + '__lt': date_boundary(end + timedelta(days=1))})
        before.append(totals(queryset.filter(**{date_field + '__lt': date_boundary(start)}), owner, amount)
                      if start else {})
        if start:
            queryset = queryset.filter(**{date_field + '__gte': date_boundary(start)})
        current.append(totals(queryset, owner, amount))
    accounts = {}
    for author in Author.objects.filter(userId__in=user_ids).order_by('pk'):
        accounts.setdefault(author.userId_id, set())
        if author.shaba and author.shaba.strip():
            accounts[author.userId_id].add(author.shaba.replace(' ', '').upper())
    rows = []
    for user in users:
        previous = calculate_revenue(*(values.get(user.pk) for values in before))
        cumulative = calculate_revenue(*(
            (old.get(user.pk) or 0) + (new.get(user.pk) or 0)
            for old, new in zip(before, current)))
        # Difference of cumulative rounded shares keeps adjacent periods additive.
        call = cumulative['call_share'] - previous['call_share']
        message = cumulative['message_share'] - previous['message_share']
        paid = current[2].get(user.pk) or 0
        gross = call + message
        available = previous['balance'] + gross
        balance = available - paid
        shabas = accounts.get(user.pk, set())
        rows.append({
            'user_id': user.pk, 'first_name': user.first_name, 'last_name': user.last_name,
            'phone': user.username, 'iban': next(iter(shabas)) if len(shabas) == 1 else '',
            'iban_ambiguous': len(shabas) > 1,
            'call_share': call, 'message_share': message, 'gross_earnings': gross,
            'opening_balance': previous['balance'], 'previous_payments': previous['deductions'],
            'deductions': previous['deductions'] + paid, 'tax': None,
            'payable': max(available, 0), 'paid_in_period': paid, 'balance': balance,
            'settlement_status': 'settled' if balance <= 0 else ('partial' if paid > 0 else 'unpaid'),
        })
    keys = ['call_share', 'message_share', 'gross_earnings', 'opening_balance',
            'previous_payments', 'deductions', 'payable', 'paid_in_period', 'balance']
    return {'currency': 'toman', 'tax_status': 'pending', 'ledger_status': 'pending',
            'results': rows, 'totals': {key: sum(row[key] for row in rows) for key in keys}}


def financial_events(kind, start=None, end=None, consultant=None, search=''):
    queryset = Transaction.objects.filter(
        type='w', userId__in=Author.objects.exclude(userId=None).values('userId'))
    if consultant:
        queryset = queryset.filter(userId=consultant)
    if search:
        queryset = queryset.filter(Q(userId__first_name__icontains=search) |
                                  Q(userId__last_name__icontains=search) |
                                  Q(userId__username__icontains=search))
    if kind == 'settlements':
        queryset = queryset.filter(settlement_document__isnull=False)
    queryset = queryset.annotate(event_at=Coalesce('settlement_document__batch__paid_at', 'created_at'))
    if start:
        queryset = queryset.filter(event_at__gte=date_boundary(start))
    if end:
        queryset = queryset.filter(event_at__lt=date_boundary(end + timedelta(days=1)))
    queryset = queryset.select_related('userId', 'settlement_document__batch').order_by('event_at', 'pk')
    events = []
    for item in queryset:
        document = getattr(item, 'settlement_document', None)
        events.append({
            'document_id': str(document.pk) if document else '',
            'first_name': item.userId.first_name, 'last_name': item.userId.last_name,
            'phone': item.userId.username, 'transaction_id': str(item.pk),
            'amount_toman': item.amount,
            'event_at': item.event_at.astimezone(ZoneInfo('Asia/Tehran')).isoformat(),
            'event_kind': ('برگشت پرداخت' if document.reverses_id else 'پرداخت تأییدشده') if document else 'کسورات قدیمی w',
            'bank_reference': document.batch.bank_reference if document else '',
            'confirmed_by': str(document.batch.confirmed_by_id) if document else '',
            'reverses': str(document.reverses_id) if document and document.reverses_id else '',
        })
    return events


def build_detailed_report(report_type='performance', **filters):
    from .report_exports import project_report
    report = build_report(**filters)
    events = financial_events(report_type, **filters) if report_type in ('payments', 'settlements') else None
    result = project_report(report_type, report, events, start=filters.get('start'), end=filters.get('end'),
                            generated_at=timezone.now().astimezone(ZoneInfo('Asia/Tehran')).isoformat())
    result['filter_description'] = 'مشاور {} | جست‌وجو {}'.format(filters.get('consultant') or 'همه', filters.get('search') or 'همه')
    return result
