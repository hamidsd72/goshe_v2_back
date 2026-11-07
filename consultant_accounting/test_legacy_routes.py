"""Regression coverage for accounting safeguards on existing public routes."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import include, path, resolve
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import Author, Category, Transaction
from call.models import CallLog
from .legacy_views import AdminTransactionViewSet, AuthorYearlyPriceViewSet
from .settlements import confirm_settlement, preview_settlement

urlpatterns = [
    path('', include('consultant_accounting.legacy_urls')),
    path('', include('api.urls')),
]

@override_settings(ROOT_URLCONF=__name__)
class LegacyAccountingRouteTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='legacy-accounting-admin', is_superuser=True)
        self.consultant = get_user_model().objects.create_user(
            username='legacy-accounting-consultant', first_name='Test', last_name='Consultant')
        author = Author.objects.create(userId=self.consultant, shaba='IR760140040004110176408212')
        author.category.add(Category.objects.create(title='Test', slug='accounting-test'))
        CallLog.objects.create(authorId=self.consultant, call_amount=20000000)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_existing_routes_resolve_to_accounting_views(self):
        self.assertIs(resolve('/admin-transaction/').func.cls, AdminTransactionViewSet)
        self.assertIs(resolve('/author-yearly-price/').func.cls, AuthorYearlyPriceViewSet)

    def test_other_api_routes_keep_original_views(self):
        from api.views import CategoryViewSet, TransactionViewSet
        self.assertIs(resolve('/category/').func.cls, CategoryViewSet)
        self.assertIs(resolve('/transaction/').func.cls, TransactionViewSet)

    def test_admin_can_create_and_edit_unlinked_legacy_transaction(self):
        response = self.client.post('/admin-transaction/', {
            'userId': self.consultant.pk, 'type': 'w', 'amount': 10000}, format='json')
        self.assertEqual(response.status_code, 201)
        url = '/admin-transaction/{}/'.format(response.data['id'])
        self.assertEqual(self.client.patch(url, {'amount': 20000}, format='json').status_code, 200)
        self.assertEqual(Transaction.objects.get().amount, 20000)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_linked_settlement_transaction_cannot_be_changed_or_deleted(self):
        preview = preview_settlement(self.admin, [
            {'user_id': self.consultant.pk, 'amount_toman': 10000}])
        batch = confirm_settlement(self.admin, preview['token'], 'LEGACY-TEST', timezone.now())
        transaction_id = batch['payments'][0]['transaction_id']
        url = '/admin-transaction/{}/'.format(transaction_id)
        self.assertEqual(self.client.patch(url, {'amount': 1}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 400)
        self.assertEqual(Transaction.objects.get(pk=transaction_id).amount, 10000)

    def test_admin_transaction_route_rejects_regular_user(self):
        self.client.force_authenticate(self.consultant)
        response = self.client.post('/admin-transaction/', {
            'userId': self.consultant.pk, 'type': 'w', 'amount': 10000}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_consultant_yearly_fee_keeps_existing_response_and_amount(self):
        self.client.force_authenticate(self.consultant)
        response = self.client.get('/author-yearly-price/')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, {'msg': 'با موفقیت پرداخت شد.'})
        payment = Transaction.objects.get(userId=self.consultant, type='w')
        self.assertEqual(payment.amount, 500000)
