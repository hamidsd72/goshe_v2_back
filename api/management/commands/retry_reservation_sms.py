"""Do not automatically resend an SMS whose acceptance is unknown."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from api.models import ReservationNotification
from api.tasks import reservation_sms


class Command(BaseCommand):
    help = 'Retry a failed/stuck reservation SMS after confirming it was not accepted.'

    def add_arguments(self, parser):
        parser.add_argument('notification_id', type=int)
        parser.add_argument('--confirm-provider-checked', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm_provider_checked']:
            raise CommandError('Confirm non-delivery with the provider before retrying.')
        notice = ReservationNotification.objects.select_for_update().get(pk=options['notification_id'])
        if notice.status not in ('unknown', 'sending'):
            raise CommandError('Only failed or stuck notifications may be retried.')
        notice.status = 'pending'
        notice.task_id = reservation_sms(notice.pk, schedule=timezone.now(), queue='reservations').pk
        notice.save(update_fields=['status', 'task_id', 'updated_at'])
        self.stdout.write('Notification requeued.')
