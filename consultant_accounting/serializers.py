from rest_framework import serializers


class ReportFiltersSerializer(serializers.Serializer):
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    consultant = serializers.IntegerField(required=False, min_value=1)
    search = serializers.CharField(required=False, max_length=100, allow_blank=True)

    def validate(self, attrs):
        from datetime import date
        if attrs.get('end') == date.max:
            raise serializers.ValidationError('تاریخ پایان خارج از محدوده مجاز است.')
        if attrs.get('start') and attrs.get('end') and attrs['start'] > attrs['end']:
            raise serializers.ValidationError('تاریخ پایان باید بعد از تاریخ شروع باشد.')
        return attrs


class BankPreviewSerializer(ReportFiltersSerializer):
    selected = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=1000)

    def validate_selected(self, values):
        return sorted(set(values))


class BankDownloadSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=1000000)


class PaymentItemSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    amount_toman = serializers.IntegerField(min_value=1, max_value=2147483647)


class SettlementPreviewSerializer(ReportFiltersSerializer):
    payments = PaymentItemSerializer(many=True, allow_empty=False)

    def validate_payments(self, values):
        ids = [item['user_id'] for item in values]
        if len(ids) > 1000 or len(ids) != len(set(ids)):
            raise serializers.ValidationError('حداکثر ۱۰۰۰ مشاور بدون تکرار مجاز است.')
        return sorted(values, key=lambda item: item['user_id'])


class SettlementConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=1000000)
    bank_reference = serializers.RegexField(r'^[A-Za-z0-9][A-Za-z0-9._/-]{2,119}$')
    paid_at = serializers.DateTimeField()
    bank_transfer_completed = serializers.BooleanField()

    def validate_bank_transfer_completed(self, value):
        if not value:
            raise serializers.ValidationError('انجام واقعی واریز باید تأیید شود.')
        return value

    def validate_paid_at(self, value):
        from django.utils import timezone
        if value > timezone.now():
            raise serializers.ValidationError('زمان واریز نمی‌تواند در آینده باشد.')
        return value


class SettlementReversalSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    bank_reference = serializers.RegexField(r'^[A-Za-z0-9][A-Za-z0-9._/-]{2,119}$')
    paid_at = serializers.DateTimeField()
    reason = serializers.CharField(max_length=500)
    correction_confirmed = serializers.BooleanField()

    def validate_correction_confirmed(self, value):
        if not value:
            raise serializers.ValidationError('ثبت سند برگشت باید تأیید شود.')
        return value

    def validate_paid_at(self, value):
        from django.utils import timezone
        if value > timezone.now():
            raise serializers.ValidationError('تاریخ رویداد نمی‌تواند در آینده باشد.')
        return value


class DetailedReportSerializer(ReportFiltersSerializer):
    report_type = serializers.ChoiceField(
        choices=['performance', 'deductions', 'payments', 'balances', 'settlements'], default='performance')


class ReportExportSerializer(DetailedReportSerializer):
    file_type = serializers.ChoiceField(choices=['xlsx', 'print'])
