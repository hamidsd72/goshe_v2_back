"""Route existing financial endpoints through accounting safeguards."""
from django.urls import path
from rest_framework.routers import SimpleRouter

from .legacy_views import AdminTransactionViewSet, AuthorYearlyPriceViewSet

app_name = 'consultant_accounting_legacy'
router = SimpleRouter()
router.register('admin-transaction', AdminTransactionViewSet, basename='admin-transaction')
urlpatterns = router.urls + [
    path('author-yearly-price/', AuthorYearlyPriceViewSet.as_view(), name='author-yearly-price'),
]
