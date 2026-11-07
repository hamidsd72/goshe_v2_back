from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import IsSuperUser
from .services import get_consultant_revenue
from .serializers import ReportFiltersSerializer, BankPreviewSerializer, BankDownloadSerializer
from .reports import build_report
from .bank import bank_row, render_bank_file


class ConsultantReportView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        filters = ReportFiltersSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        return Response(build_report(**filters.validated_data))


class ConsultantRevenueView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request, user_id):
        user = get_object_or_404(get_user_model(), pk=user_id)
        return Response(get_consultant_revenue(user.pk))


class BankPreviewView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        from django.core import signing
        filters = BankPreviewSerializer(data=request.data)
        filters.is_valid(raise_exception=True)
        params = dict(filters.validated_data)
        selected = params.pop('selected')
        report = build_report(**params)
        current = {row['user_id']: row for row in build_report()['results']}
        found = {row['user_id']: row for row in report['results']}
        valid, excluded = [], []
        for user_id in selected:
            if user_id not in found or user_id not in current:
                excluded.append({'user_id': user_id, 'errors': ['مشاور در نتایج گزارش موجود نیست.']})
                continue
            row = bank_row(found[user_id], current[user_id]['balance'])
            (excluded if row['errors'] else valid).append(row)
        token = signing.dumps({'admin': request.user.pk, 'rows': valid},
                              salt='consultant-bank-export', compress=True) if valid else None
        response = Response({'rows': valid, 'excluded': excluded, 'currency': 'rial',
                             'total_rial': sum(row['amount_rial'] for row in valid), 'token': token})
        response['Cache-Control'] = 'no-store'
        return response


class BankDownloadView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        from django.core import signing
        from django.http import HttpResponse
        filters = BankDownloadSerializer(data=request.data)
        filters.is_valid(raise_exception=True)
        try:
            snapshot = signing.loads(filters.validated_data['token'],
                                     salt='consultant-bank-export', max_age=600)
        except signing.BadSignature:
            return Response({'detail': 'پیش‌نمایش نامعتبر یا منقضی است. دوباره پیش‌نمایش بگیرید.'}, status=400)
        if snapshot['admin'] != request.user.pk:
            return Response({'detail': 'پیش‌نمایش متعلق به مدیر دیگری است.'}, status=403)
        current = {row['user_id']: row for row in build_report()['results']}
        for saved in snapshot['rows']:
            row = current.get(saved['user_id'])
            if row is None:
                return Response({'detail': 'اطلاعات مشاور تغییر کرده است. دوباره پیش‌نمایش بگیرید.'}, status=409)
            verified = bank_row(row, row['balance'])
            if (verified['errors'] or verified['amount_rial'] < saved['amount_rial'] or
                    any(verified[key] != saved[key] for key in ('iban', 'first_name', 'last_name'))):
                return Response({'detail': 'مانده یا اطلاعات بانکی تغییر کرده است. دوباره پیش‌نمایش بگیرید.'}, status=409)
        response = HttpResponse(render_bank_file(snapshot['rows']), content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="parsian-consultants.txt"'
        response['Cache-Control'] = 'no-store'
        return response


class SettlementPreviewView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        from .serializers import SettlementPreviewSerializer
        from .settlements import preview_settlement
        data = SettlementPreviewSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        response = Response(preview_settlement(request.user, **data.validated_data))
        response['Cache-Control'] = 'no-store'
        return response


class SettlementConfirmView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        from .serializers import SettlementConfirmSerializer
        from .settlements import confirm_settlement
        data = SettlementConfirmSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(confirm_settlement(request.user, **data.validated_data))


class SettlementReversalView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request, payment_id):
        from .serializers import SettlementReversalSerializer
        from .settlements import reverse_payment
        data = SettlementReversalSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(reverse_payment(request.user, payment_id, **data.validated_data))


class SettlementHistoryView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        from rest_framework.pagination import PageNumberPagination
        from .models import SettlementBatch
        from .settlements import serialize_batch
        batches = SettlementBatch.objects.order_by('-pk').prefetch_related('payments')
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(batches, request)
        return paginator.get_paginated_response([serialize_batch(batch) for batch in page])


class DetailedReportView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        from .serializers import DetailedReportSerializer
        from .reports import build_detailed_report
        filters = DetailedReportSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        response = Response(build_detailed_report(**filters.validated_data))
        response['Cache-Control'] = 'no-store'
        return response


class ReportExportView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        from django.http import HttpResponse
        from .serializers import ReportExportSerializer
        from .reports import build_detailed_report
        from .report_exports import render_xlsx, render_print_html
        filters = ReportExportSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        params = dict(filters.validated_data)
        file_type = params.pop('file_type')
        report = build_detailed_report(**params)
        if file_type == 'xlsx':
            response = HttpResponse(render_xlsx(report), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="consultant-{}.xlsx"'.format(params['report_type'])
        else:
            response = Response({'html': render_print_html(report)})
        response['Cache-Control'] = 'no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
