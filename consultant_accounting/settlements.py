"""Atomic settlement and reversal services using the consultant User as mutex."""
import hashlib
import json
import time
import uuid
from datetime import timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException, ValidationError

from api.models import Transaction
from .bank import bank_row
from .models import SettlementBatch, SettlementPayment
from .reports import build_report
from .services import get_consultant_revenue


class SettlementConflict(APIException):
    status_code = 409
    default_detail = 'درخواست تکراری یا مانده و اطلاعات تغییر کرده است. گزارش را تازه کنید.'


def preview_settlement(admin, payments, **filters):
    report = {row['user_id']: row for row in build_report(**filters)['results']}
    current = {row['user_id']: row for row in build_report()['results']}
    rows = []
    for item in payments:
        user_id = item['user_id']
        if user_id not in report or user_id not in current:
            raise ValidationError('مشاور در گزارش موجود نیست.')
        row = bank_row(report[user_id], current[user_id]['balance'])
        if row['errors'] or item['amount_toman'] * 10 > row['amount_rial']:
            raise ValidationError({'user_id': user_id, 'detail': row['errors'] or ['مبلغ از مانده بیشتر است.']})
        row['amount_toman'] = item['amount_toman']
        row['amount_rial'] = item['amount_toman'] * 10
        rows.append(row)
    snapshot = {'request_id': str(uuid.uuid4()), 'admin': admin.pk,
                'issued_at': time.time(), 'rows': rows}
    return {'token': signing.dumps(snapshot, salt='consultant-settlement', compress=True),
            'rows': rows, 'request_id': snapshot['request_id'],
            'total_toman': sum(row['amount_toman'] for row in rows)}


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def timestamp(value):
    return value.astimezone(datetime_timezone.utc).isoformat()


def serialize_batch(batch):
    return {'id': batch.pk, 'request_id': str(batch.request_id),
            'bank_reference': batch.bank_reference, 'confirmed_by': batch.confirmed_by_id,
            'paid_at': timestamp(batch.paid_at), 'created_at': timestamp(batch.created_at),
            'payments': [{'id': item.pk, 'user_id': item.consultant_id,
                          'amount_toman': item.amount_toman, 'balance_after': item.balance_after,
                          'reverses': item.reverses_id, 'transaction_id': item.transaction_id}
                         for item in batch.payments.all()]}


def confirm_settlement(admin, token, bank_reference, paid_at, **unused):
    try:
        snapshot = signing.loads(token, salt='consultant-settlement')
    except signing.BadSignature:
        raise ValidationError('پیش‌نمایش پرداخت معتبر نیست.')
    if snapshot['admin'] != admin.pk:
        raise ValidationError('پیش‌نمایش متعلق به مدیر دیگری است.')
    digest = fingerprint({'snapshot': snapshot, 'bank_reference': bank_reference,
                          'paid_at': timestamp(paid_at)})
    try:
        with transaction.atomic():
            ids = sorted(row['user_id'] for row in snapshot['rows'])
            locked = list(get_user_model().objects.select_for_update().filter(pk__in=ids).order_by('pk'))
            if len(locked) != len(ids):
                raise SettlementConflict()
            existing = SettlementBatch.objects.select_for_update().filter(request_id=snapshot['request_id']).first()
            if existing:
                if existing.payload_hash != digest:
                    raise SettlementConflict()
                return serialize_batch(existing)
            if time.time() - snapshot['issued_at'] > 600:
                raise ValidationError('پیش‌نمایش پرداخت منقضی است.')
            current = {row['user_id']: row for row in build_report()['results']}
            for row in snapshot['rows']:
                latest = current.get(row['user_id'])
                if latest is None:
                    raise SettlementConflict()
                checked = bank_row(latest, latest['balance'])
                if (checked['errors'] or checked['amount_rial'] < row['amount_rial'] or
                        any(checked[key] != row[key] for key in ('iban', 'first_name', 'last_name'))):
                    raise SettlementConflict()
            batch = SettlementBatch.objects.create(
                request_id=snapshot['request_id'], bank_reference=bank_reference,
                confirmed_by=admin, paid_at=paid_at, payload_hash=digest)
            for row in snapshot['rows']:
                balance = current[row['user_id']]['balance']
                payment = Transaction.objects.create(userId_id=row['user_id'], type='w', amount=row['amount_toman'])
                SettlementPayment.objects.create(
                    batch=batch, consultant_id=row['user_id'], transaction=payment,
                    amount_toman=row['amount_toman'], iban=row['iban'],
                    first_name=row['first_name'], last_name=row['last_name'],
                    balance_before=balance, balance_after=balance - row['amount_toman'])
            return serialize_batch(batch)
    except IntegrityError:
        raise SettlementConflict('شناسه عملیات یا مرجع بانکی قبلاً ثبت شده است.')


def reverse_payment(admin, payment_id, request_id, bank_reference, paid_at, reason, **unused):
    original = SettlementPayment.objects.filter(pk=payment_id, reverses=None).first()
    if original is None:
        raise ValidationError('سند پرداخت اصلی یافت نشد.')
    if paid_at < original.batch.paid_at:
        raise ValidationError('تاریخ برگشت باید پس از تاریخ پرداخت اصلی باشد.')
    digest = fingerprint({'payment': payment_id, 'admin': admin.pk,
                          'reason': reason, 'paid_at': timestamp(paid_at), 'bank_reference': bank_reference})
    try:
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=original.consultant_id)
            existing = SettlementBatch.objects.select_for_update().filter(request_id=request_id).first()
            if existing:
                if existing.payload_hash != digest:
                    raise SettlementConflict()
                return serialize_batch(existing)
            if SettlementPayment.objects.filter(reverses=original).exists():
                raise SettlementConflict('برای این پرداخت سند برگشت ثبت شده است.')
            balance = get_consultant_revenue(original.consultant_id)['balance']
            batch = SettlementBatch.objects.create(
                request_id=request_id, bank_reference=bank_reference, confirmed_by=admin,
                paid_at=paid_at, payload_hash=digest)
            correction = Transaction.objects.create(
                userId_id=original.consultant_id, type='w', amount=-original.amount_toman)
            SettlementPayment.objects.create(
                batch=batch, consultant_id=original.consultant_id, transaction=correction,
                amount_toman=original.amount_toman, iban=original.iban,
                first_name=original.first_name, last_name=original.last_name,
                balance_before=balance, balance_after=balance + original.amount_toman,
                reverses=original, reason=reason)
            return serialize_batch(batch)
    except IntegrityError:
        raise SettlementConflict()
