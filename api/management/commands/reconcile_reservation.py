"""Explicit operator recovery after inspecting the telephony provider's records."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from call.models import CallLog
from api import reservation_services as services


class Command(BaseCommand):
    help = 'Reconcile a stuck reservation only after checking provider records.'

    def add_arguments(self, parser):
        parser.add_argument('reservation_id', type=int)
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--provider-id', type=int)
        group.add_argument('--not-created', action='store_true')
        parser.add_argument('--confirm-provider-checked', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm_provider_checked']:
            raise CommandError('Check provider records first; then pass --confirm-provider-checked.')
        credit = services.lock_credit(options['reservation_id'])
        if credit.status not in ('dialing', 'uncertain'):
            raise CommandError('Only dialing/uncertain reservations can be reconciled.')
        provider_id = options['provider_id']
        if provider_id is not None:
            if provider_id <= 0 or CallLog.objects.exclude(pk=credit.call_id).filter(Sitak_id=provider_id).exists():
                raise CommandError('Invalid or already-used provider ID.')
            CallLog.objects.filter(pk=credit.call_id).update(Sitak_id=provider_id, type='کد 1 در حال تماس')
            credit.status = 'in_call'; credit.failure_code = 'operator_bound_provider'
            credit.save(update_fields=['status', 'failure_code', 'updated_at'])
            self.stdout.write('Provider ID attached. Process the authenticated final callback to settle unused credit.')
        else:
            services.refund(credit, credit.amount_rial, 'failed')
            credit.failure_code = 'operator_confirmed_no_call'
            credit.save(update_fields=['failure_code'])
            CallLog.objects.filter(pk=credit.call_id).update(call_amount=0, type='رزرو ناموفق؛ اعتبار برگشت خورد')
            self.stdout.write('Reserved credit refunded once.')
