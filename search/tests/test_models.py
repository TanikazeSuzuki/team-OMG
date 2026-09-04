from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from search.models import SavedSearch

User = get_user_model()


class SavedSearchModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")

    def test_str_includes_owner_and_keyword(self):
        saved_search = SavedSearch.objects.create(owner=self.owner, keyword="花火")
        self.assertIn("花火", str(saved_search))

    def test_period_from_after_period_to_is_invalid(self):
        saved_search = SavedSearch(
            owner=self.owner,
            period_from="2026-02-01",
            period_to="2026-01-01",
        )
        with self.assertRaises(ValidationError):
            saved_search.full_clean()

    def test_age_min_greater_than_age_max_is_invalid(self):
        saved_search = SavedSearch(owner=self.owner, age_min=10, age_max=5)
        with self.assertRaises(ValidationError):
            saved_search.full_clean()

    def test_valid_saved_search_passes_full_clean(self):
        saved_search = SavedSearch(
            owner=self.owner,
            keyword="花火",
            location="東京",
            period_from="2026-01-01",
            period_to="2026-01-31",
            age_min=3,
            age_max=10,
        )
        saved_search.full_clean()  # 例外が発生しなければOK
