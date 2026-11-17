from background_task import background
from django.db import transaction
from django.utils import timezone
from .models import ReservationNotification
from . import reservation_services as services
from . import reservation_providers as providers


@background(queue='reservations')
def reservation_call(credit_id):
    services.dispatch(credit_id)


@background(queue='reservations')
def reservation_sms(notice_id):
    with transaction.atomic():
        notice = ReservationNotification.objects.select_for_update().select_related('credit__visit').get(pk=notice_id)
        if notice.status != 'pending':
            return
        if notice.kind.startswith('booking_') and notice.credit.status in ('cancelled', 'failed', 'completed'):
            notice.status = 'skipped'
            notice.save(update_fields=['status'])
            return
        notice.status = 'sending'
        notice.attempts += 1
        notice.save(update_fields=['status', 'attempts', 'updated_at'])
    args = services.date_arguments(notice.credit)
    try:
        receipt = providers.send_pattern(notice.number, 589593 if notice.kind == 'cancellation' else 589588,
            args[:1] if notice.kind == 'cancellation' else args)
    except Exception:
        # Do not persist provider exceptions: URLs/bodies can contain credentials.
        ReservationNotification.objects.filter(pk=notice_id).update(status='unknown', updated_at=timezone.now())
        return
    ReservationNotification.objects.filter(pk=notice_id).update(status='sent', receipt=receipt, updated_at=timezone.now())
