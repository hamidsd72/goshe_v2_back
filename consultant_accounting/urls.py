from django.urls import path

from .views import ConsultantRevenueView, ConsultantReportView, BankPreviewView, BankDownloadView
from .views import SettlementPreviewView, SettlementConfirmView, SettlementHistoryView, SettlementReversalView
from .views import DetailedReportView, ReportExportView

app_name = 'consultant_accounting'
urlpatterns = [
    path('reports/', DetailedReportView.as_view(), name='detailed-report'),
    path('reports/export/', ReportExportView.as_view(), name='report-export'),
    path('settlements/preview/', SettlementPreviewView.as_view(), name='settlement-preview'),
    path('settlements/confirm/', SettlementConfirmView.as_view(), name='settlement-confirm'),
    path('settlements/', SettlementHistoryView.as_view(), name='settlement-history'),
    path('settlements/<int:payment_id>/reverse/', SettlementReversalView.as_view(), name='settlement-reverse'),
    path('bank/preview/', BankPreviewView.as_view(), name='bank-preview'),
    path('bank/download/', BankDownloadView.as_view(), name='bank-download'),
    path('report/', ConsultantReportView.as_view(), name='report'),
    path('consultants/<int:user_id>/revenue/', ConsultantRevenueView.as_view(),
         name='consultant-revenue'),
]
