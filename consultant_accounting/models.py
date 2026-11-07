"""Append-only settlement documents. Amounts in these tables are toman."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class DocumentQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('Financial documents are immutable; create a reversal.')

    def delete(self):
        raise ValidationError('Financial documents cannot be deleted.')

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError('Financial documents are immutable.')


class FinancialDocument(models.Model):
    objects = DocumentQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Financial documents are immutable; create a reversal.')
        kwargs['force_insert'] = True
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Financial documents cannot be deleted.')


class SettlementBatch(FinancialDocument):
    request_id = models.UUIDField(unique=True)
    bank_reference = models.CharField(max_length=120, unique=True)
    payload_hash = models.CharField(max_length=64)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                     related_name='confirmed_settlement_batches')
    paid_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class SettlementPayment(FinancialDocument):
    batch = models.ForeignKey(SettlementBatch, on_delete=models.PROTECT, related_name='payments')
    consultant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name='settlement_payments')
    transaction = models.OneToOneField('api.Transaction', on_delete=models.PROTECT,
                                      related_name='settlement_document')
    amount_toman = models.PositiveIntegerField()
    iban = models.CharField(max_length=26)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    balance_before = models.BigIntegerField()
    balance_after = models.BigIntegerField()
    reverses = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT,
                                   related_name='reversal')
    reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['batch', 'consultant'], name='unique_batch_consultant'),
            models.CheckConstraint(check=models.Q(amount_toman__gt=0), name='settlement_positive_amount'),
        ]
