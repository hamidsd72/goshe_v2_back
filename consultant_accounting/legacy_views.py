"""Settlement safeguards for existing API routes, owned by accounting."""
from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from rest_framework.exceptions import ValidationError

from api.permissions import IsSuperUser
from api.views import AdminTransactionViewSet as LegacyAdminTransactionViewSet
from api.views import AuthorYearlyPriceViewSet as LegacyAuthorYearlyPriceViewSet


class AdminTransactionViewSet(LegacyAdminTransactionViewSet):
    permission_classes = [IsSuperUser]

    def perform_create(self, serializer):
        with db_transaction.atomic():
            user = serializer.validated_data.get('userId')
            if user:
                get_user_model().objects.select_for_update().get(pk=user.pk)
            serializer.save()

    def perform_update(self, serializer):
        from django.apps import apps
        with db_transaction.atomic():
            old_user = serializer.instance.userId_id
            new_user = serializer.validated_data.get('userId', serializer.instance.userId)
            ids = sorted({value for value in [old_user, new_user.pk if new_user else None] if value})
            list(get_user_model().objects.select_for_update().filter(pk__in=ids).order_by('pk'))
            if apps.is_installed('consultant_accounting') and hasattr(serializer.instance, 'settlement_document'):
                raise ValidationError('برای اصلاح پرداخت، سند برگشت ثبت کنید.')
            serializer.save()

    def perform_destroy(self, instance):
        from django.apps import apps
        with db_transaction.atomic():
            if instance.userId_id:
                get_user_model().objects.select_for_update().get(pk=instance.userId_id)
            if apps.is_installed('consultant_accounting') and hasattr(instance, 'settlement_document'):
                raise ValidationError('سند پرداخت قابل حذف نیست.')
            instance.delete()


class AuthorYearlyPriceViewSet(LegacyAuthorYearlyPriceViewSet):
    """Keep the existing consultant-facing permissions and yearly fee behavior."""

    @db_transaction.atomic
    def get(self, request):
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        return super().get(request)
