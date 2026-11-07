"""Protect legacy Transaction rows backing immutable settlement documents."""
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from api.models import Transaction
from .models import SettlementPayment


@receiver(pre_save, sender=Transaction)
@receiver(pre_delete, sender=Transaction)
def protect_settlement_transaction(sender, instance, **kwargs):
    if instance.pk and SettlementPayment.objects.filter(transaction_id=instance.pk).exists():
        raise ValidationError('Settlement transactions require a separate reversal document.')
