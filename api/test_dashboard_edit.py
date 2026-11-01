"""Characterize the existing endpoint, including its duplicate-record defect.

Run with --settings=api.dashboard_test_settings (SQLite in memory only).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from api.models import Author
from api.views import CreateAuthorViewSet


class DashboardAuthorPatchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="dashboard-test")
        self.other = get_user_model().objects.create_user(username="other-test")
        self.factory = APIRequestFactory()
        self.view = CreateAuthorViewSet.as_view({"patch": "partial_update"})

    def request(self, user=None, **data):
        request = self.factory.patch("/createauthor/{}/".format(self.user.pk), data, format="json")
        force_authenticate(request, user=user or self.user)
        return self.view(request, userId=str(self.user.pk))

    def test_single_author_services_can_be_updated_by_owner(self):
        author = Author.objects.create(userId=self.user, services=False)
        response = self.request(services=True)
        self.assertEqual(response.status_code, 200)
        author.refresh_from_db()
        self.assertTrue(author.services)

    def test_duplicate_author_reproduces_multiple_objects_returned(self):
        Author.objects.create(userId=self.user, services=False)
        Author.objects.create(userId=self.user, services=False)
        with self.assertRaises(Author.MultipleObjectsReturned):
            self.request(services=True)
        self.assertEqual(Author.objects.filter(userId=self.user, services=False).count(), 2)

    def test_different_owner_cannot_change_single_author(self):
        author = Author.objects.create(userId=self.user, services=False)
        self.assertEqual(self.request(user=self.other, services=True).status_code, 403)
        author.refresh_from_db()
        self.assertFalse(author.services)

    def test_missing_author_returns_404(self):
        self.assertEqual(self.request(services=True).status_code, 404)

    def test_serializer_validation_rejects_invalid_visit_type(self):
        Author.objects.create(userId=self.user)
        self.assertEqual(self.request(visit_type="invalid").status_code, 400)

    def test_status_is_excluded_and_not_changed_by_dashboard_payload(self):
        author = Author.objects.create(userId=self.user, status=False)
        self.assertEqual(self.request(status=True, services=True).status_code, 200)
        author.refresh_from_db()
        self.assertFalse(author.status)
        self.assertTrue(author.services)
