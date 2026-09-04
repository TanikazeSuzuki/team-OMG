from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from events.models import Event
from search.management.commands.load_sheet_test_data import ORGANIZER_EMAIL
from search.spreadsheet_test_data import (
    build_description,
    load_event_specs,
    load_search_cases,
    parse_age_range,
)


class SpreadsheetTestDataParserTests(TestCase):
    def test_all_events_and_search_cases_are_loaded(self):
        specs = load_event_specs()
        cases = load_search_cases()

        self.assertEqual(len(specs), 30)
        self.assertEqual({spec.number for spec in specs}, set(range(1, 31)))
        self.assertEqual(len(cases), 14)

    def test_numeric_ages_are_parsed_without_guessing_categories(self):
        self.assertEqual(parse_age_range("3歳〜12歳（ファミリー）"), (3, 12))
        self.assertEqual(parse_age_range("20歳以上"), (20, None))
        self.assertEqual(parse_age_range("ビジネス向け"), (None, None))

    def test_unmapped_columns_are_kept_in_description(self):
        spec = next(spec for spec in load_event_specs() if spec.number == 20)
        description = build_description(spec)

        self.assertIn("ターゲット年齢: ビジネス向け", description)
        self.assertIn("参加費用: 1,000円（事前登録者は無料）", description)
        self.assertIn("公式URL: https://www.japanpack.jp/", description)
        self.assertIn("仮タグ: 大人", description)


class LoadSheetTestDataCommandTests(TestCase):
    def test_command_loads_all_events_and_is_idempotent(self):
        output = StringIO()
        call_command("load_sheet_test_data", stdout=output)
        call_command("load_sheet_test_data", stdout=output)

        events = Event.objects.filter(organizer__email=ORGANIZER_EMAIL)
        self.assertEqual(events.count(), 30)
        self.assertEqual(
            set(events.get(title="JAPAN PACK 2026 (日本国際包装機械展)").tags.values_list("name", flat=True)),
            {"IT", "事前"},
        )


class SeedDemoDataCommandTests(TestCase):
    def test_command_uses_email_users_and_is_idempotent(self):
        output = StringIO()

        call_command("seed_demo_data", stdout=output)
        call_command("seed_demo_data", stdout=output)

        self.assertEqual(
            Event.objects.filter(title__startswith="【デモ】").count(),
            8,
        )
        self.assertIn("email=demo-participant@example.com", output.getvalue())
        self.assertIn("email=demo-organizer@example.com", output.getvalue())
