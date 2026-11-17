"""Booking, refunds and call settlement share a stable User-row lock order."""
from datetime import datetime, timedelta
import re
import pytz
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError, APIException
from account.services import normalize_iran_mobile
from call.models import Number, CallLog
from extensions.jalali import Gregorian
from .models import Author, AuthorVisit, ReservationCredit, ReservationNotification
from . import reservation_providers as providers

TEHRAN = pytz.timezone('Asia/Tehran')
DURATIONS = (10, 30, 60)
DAYS = ('treeDay', 'fourDay', 'fiveDay', 'sixDay', 'sevenDay', 'oneDay', 'twoDay')
BLOCKING = ('confirmed', 'dialing', 'in_call', 'uncertain')


class SlotConflict(APIException):
    status_code = 409
    default_detail = 'این بازه زمانی قبلاً رزرو شده است؛ زمان دیگری انتخاب کنید.'


def lock_users(*ids):
    return {u.pk: u for u in get_user_model().objects.select_for_update().filter(pk__in=ids).order_by('pk')}


def work_interval(author, day):
    value = getattr(author, DAYS[day.weekday()]) or ''
    if not re.fullmatch(r'\d{2}:\d{2},\d{2}:\d{2}', value):
        return None
    try:
        start, end = [TEHRAN.localize(datetime.combine(day, datetime.strptime(t, '%H:%M').time())) for t in value.split(',')]
    except ValueError:
        return None
    # Empty/equal/reversed hours are closed, not an inferred overnight shift.
    return (start, end) if start < end else None


def check_time(author, start, duration):
    start = timezone.localtime(start, TEHRAN)
    today = timezone.localtime(timezone.now(), TEHRAN).date()
    if duration not in DURATIONS or not today < start.date() <= today + timedelta(days=14):
        raise ValidationError('رزرو فقط از فردا تا ۱۴ روز آینده و برای ۱۰، ۳۰ یا ۶۰ دقیقه ممکن است.')
    end = start + timedelta(minutes=duration)
    interval = work_interval(author, start.date())
    if start.second or start.microsecond or start.minute % 10 or not interval or not (interval[0] <= start < end <= interval[1]):
        raise ValidationError('زمان انتخاب‌شده در ساعات کاری مشاور نیست.')
    return end


def conflicts(consultant_id, payer_id, start, end):
    return ReservationCredit.objects.filter(status__in=BLOCKING, visit__visitTime__lt=end, ends_at__gt=start).filter(
        Q(consultant_id__in=[consultant_id, payer_id]) | Q(payer_id__in=[consultant_id, payer_id])
    ).exists()


def legacy_conflict(consultant_id, start, end):
    # Historical bookings have no duration: conservatively protect one hour.
    return AuthorVisit.objects.filter(credit__isnull=True, AuthorUserId_id=consultant_id,
        visitTime__lt=end, visitTime__gt=start - timedelta(minutes=60)).exists()


def enqueue_notice(credit, kind, number):
    from .tasks import reservation_sms
    notice, created = ReservationNotification.objects.get_or_create(credit=credit, kind=kind, defaults={'number': number})
    if created:
        task = reservation_sms(notice.pk, schedule=timezone.now(), queue='reservations')
        notice.task_id = task.pk
        notice.save(update_fields=['task_id'])


@transaction.atomic
def book(user, author_id, number, start, duration, request_key, quoted_amount_rial=None):
    from .tasks import reservation_call
    author = Author.objects.get(pk=author_id)
    if not author.userId_id or author.userId_id == user.pk:
        raise ValidationError('مشاور معتبر نیست.')
    consultant_id = author.userId_id
    users = lock_users(user.pk, consultant_id)
    # Re-read profile after acquiring the consultant's shared scheduling mutex.
    author.refresh_from_db()
    if author.userId_id != consultant_id:
        raise ValidationError('اطلاعات مشاور تغییر کرده است؛ دوباره تلاش کنید.')
    existing = ReservationCredit.objects.filter(request_key=request_key).first()
    if existing:
        v = existing.visit
        if existing.payer_id != user.pk or (v.AuthorId_id, v.number, v.visitTime, existing.duration) != (author.pk, number, start, duration):
            raise ValidationError('شناسه درخواست قبلاً برای رزرو دیگری استفاده شده است.')
        return existing
    if not providers.configured():
        raise ValidationError('سرویس رزرو هنوز توسط مدیر سامانه پیکربندی نشده است.')
    if not author.status or author.visit_type not in ('c', 'b') or author.call_price <= 0 or not users[author.userId_id].is_active:
        raise ValidationError('مشاور برای رزرو تلفنی فعال نیست.')
    if not re.fullmatch(r'[1-9][0-9]{9}', number) or (number != users[user.pk].username and not Number.objects.filter(userId=user, number=number).exists()):
        raise ValidationError('شماره تماس باید از شماره‌های ثبت‌شده خودتان باشد.')
    try:
        consultant_number = normalize_iran_mobile(users[author.userId_id].username)[1:]
        sms_number = normalize_iran_mobile(number if number.startswith('9') else users[user.pk].username)
    except ValueError:
        raise ValidationError('شماره موبایل معتبر برای اطلاع‌رسانی رزرو ثبت نشده است.')
    end = check_time(author, start, duration)
    if conflicts(author.userId_id, user.pk, start, end) or legacy_conflict(author.userId_id, start, end):
        raise SlotConflict()
    rate = author.call_price * 10  # Author rate is toman; wallet/provider credit is rial.
    amount = rate * duration
    if quoted_amount_rial is not None and quoted_amount_rial != amount:
        raise SlotConflict('تعرفه مشاور تغییر کرده است؛ زمان‌ها و مبلغ را دوباره دریافت کنید.')
    if amount > 2147483647 or users[user.pk].amount < amount:
        raise ValidationError('موجودی کیف پول برای این رزرو کافی نیست.')
    get_user_model().objects.filter(pk=user.pk).update(amount=F('amount') - amount)
    visit = AuthorVisit.objects.create(AuthorId=author, AuthorUserId_id=author.userId_id,
        userId=user, number=number, visitTime=start, active=True, autoDial=True)
    credit = ReservationCredit.objects.create(visit=visit, payer=user, consultant_id=author.userId_id,
        request_key=request_key, duration=duration, ends_at=end, rate_rial=rate, amount_rial=amount,
        consultant_number=consultant_number, customer_sms_number=sms_number)
    # Queue rows commit/rollback with the wallet and reservation, on the same DB.
    credit.task_id = reservation_call(credit.pk, schedule=start, queue='reservations', priority=10).pk
    credit.save(update_fields=['task_id'])
    enqueue_notice(credit, 'booking_customer', sms_number)
    enqueue_notice(credit, 'booking_consultant', consultant_number)
    return credit


def lock_credit(pk):
    snapshot = ReservationCredit.objects.get(pk=pk)
    lock_users(snapshot.payer_id, snapshot.consultant_id)
    return ReservationCredit.objects.select_for_update().select_related('visit').get(pk=pk)


def refund(credit, amount, status):
    if amount < 0 or amount > credit.amount_rial - credit.refunded_rial:
        raise ValidationError('مبلغ برگشتی معتبر نیست.')
    get_user_model().objects.filter(pk=credit.payer_id).update(amount=F('amount') + amount)
    credit.refunded_rial += amount
    credit.status = status
    credit.save(update_fields=['refunded_rial', 'status', 'updated_at'])
    AuthorVisit.objects.filter(pk=credit.visit_id).update(active=False, autoDial=False)


@transaction.atomic
def cancel(pk, consultant):
    from background_task.models import Task
    credit = lock_credit(pk)
    if credit.consultant_id != consultant.pk:
        raise ValidationError('دسترسی لغو این رزرو را ندارید.')
    if credit.status == 'cancelled':
        return credit
    if credit.status != 'confirmed' or credit.visit.visitTime <= timezone.now():
        raise ValidationError('فقط رزرو شروع‌نشده قابل لغو است.')
    refund(credit, credit.amount_rial, 'cancelled')
    Task.objects.filter(pk=credit.task_id, task_name='api.tasks.reservation_call').delete()
    enqueue_notice(credit, 'cancellation', credit.customer_sms_number)
    return credit


def date_arguments(credit):
    local = timezone.localtime(credit.visit.visitTime, TEHRAN)
    y, m, d = Gregorian(local.year, local.month, local.day).persian_tuple()
    return ['{:04d}/{:02d}/{:02d}'.format(y, m, d), local.strftime('%H:%M')]


def busy(user_ids):
    return CallLog.objects.filter(Q(userId_id__in=user_ids) | Q(authorId_id__in=user_ids),
        call_amount__isnull=True).filter(Q(type__contains='در حال تماس') | Q(type='reservation:dialing')).exists()


def dispatch(pk):
    with transaction.atomic():
        credit = lock_credit(pk)
        if credit.status != 'confirmed':
            return
        now = timezone.now()
        if now < credit.visit.visitTime:
            raise ValueError('reservation_not_due')
        if now > credit.visit.visitTime + timedelta(minutes=5) or busy([credit.payer_id, credit.consultant_id]):
            credit.failure_code = 'late_or_busy'
            credit.save(update_fields=['failure_code'])
            refund(credit, credit.amount_rial, 'failed')
            return
        call = CallLog.objects.create(userId_id=credit.payer_id, authorId_id=credit.consultant_id,
            FirstCredit=credit.amount_rial, AmountPerMin=credit.rate_rial, type='رزرو در حال تماس')
        credit.call = call
        credit.status = 'dialing'
        credit.save(update_fields=['call', 'status', 'updated_at'])
    try:
        sitak_id = providers.create_call(call, credit)
    except Exception:
        # HTTP timeouts may occur after provider acceptance. Hold funds for reconciliation.
        ReservationCredit.objects.filter(pk=pk, status='dialing').update(status='uncertain', failure_code='provider_result_unknown')
        return
    with transaction.atomic():
        credit = lock_credit(pk)
        CallLog.objects.filter(pk=call.pk).update(Sitak_id=sitak_id)
        if credit.status != 'completed':
            CallLog.objects.filter(pk=call.pk).update(type='کد 1 در حال تماس')
            credit.status = 'in_call'
            credit.save(update_fields=['status', 'updated_at'])


@transaction.atomic
def settle(call_id, last_credit, call_amount, detail):
    credit = lock_credit(ReservationCredit.objects.get(call_id=call_id).pk)
    if credit.status == 'completed':
        return credit
    if credit.status not in ('dialing', 'in_call', 'uncertain'):
        raise ValidationError('وضعیت رزرو برای تسویه معتبر نیست.')
    if not 0 <= last_credit <= credit.amount_rial or call_amount < 0 or last_credit + call_amount != credit.amount_rial:
        raise ValidationError('مبالغ گزارش تماس با اعتبار رزرو مطابقت ندارد.')
    CallLog.objects.filter(pk=call_id).update(call_amount=call_amount, type=detail[:50])
    refund(credit, last_credit, 'completed')
    return credit
