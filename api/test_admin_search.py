from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from api.admin import AuthorAdmin
from api.models import Author


class AuthorAdminSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="9125550001", first_name="آزمایش", last_name="جستجو",
        )
        cls.author = Author.objects.create(userId=cls.user, service_time=timezone.now())
        other = get_user_model().objects.create_user(username="9135550002")
        Author.objects.create(userId=other, service_time=timezone.now())

    def search(self, term):
        model_admin = AuthorAdmin(Author, admin.site)
        request = RequestFactory().get("/admin/api/author/", {"q": term})
        queryset, _ = model_admin.get_search_results(request, Author.objects.all(), term)
        return set(queryset.values_list("pk", flat=True))

    def test_username_and_partial_phone_search(self):
        for term in ["9125550001", "1255500"]:
            with self.subTest(term=term):
                self.assertEqual(self.search(term), {self.author.pk})

    def test_first_last_and_combined_name_search(self):
        for term in ["آزمایش", "جستجو", "آزمایش جستجو"]:
            with self.subTest(term=term):
                self.assertEqual(self.search(term), {self.author.pk})

    def test_no_match_returns_empty_queryset(self):
        self.assertEqual(self.search("not-a-match"), set())

    def test_empty_search_keeps_all_records(self):
        self.assertEqual(self.search(""), set(Author.objects.values_list("pk", flat=True)))

    def test_duplicate_author_records_remain_visible_and_unchanged(self):
        duplicate = Author.objects.create(userId=self.user, service_time=timezone.now())
        self.assertEqual(self.search("9125550001"), {self.author.pk, duplicate.pk})
        self.assertEqual(Author.objects.filter(userId=self.user).count(), 2)

    def test_status_is_a_filter_not_a_text_search_field(self):
        self.assertIn("status", AuthorAdmin.list_filter)
        self.assertNotIn("status", AuthorAdmin.search_fields)
