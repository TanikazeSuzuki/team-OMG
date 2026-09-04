from django.core.management.base import BaseCommand, CommandError

from events.models import Tag
from search.criteria import SearchCriteria
from search.services import SearchService
from search.spreadsheet_test_data import (
    load_event_specs,
    load_search_cases,
    normalized_tag_names,
    parse_sheet_date,
)


class Command(BaseCommand):
    help = "共有スプレッドシート下部の14検索ケースを現在の検索機能で確認する"

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="1件でも不一致なら終了コードを失敗にする",
        )

    def handle(self, *args, **options):
        specs = load_event_specs()
        number_by_title = {spec.title: spec.number for spec in specs}
        imported_titles = set(number_by_title)
        passed = 0
        active = 0
        skipped = 0

        for case in load_search_cases():
            if case.target_text:
                skipped += 1
                self.stdout.write(
                    f"{case.number:02d}. 対象外 "
                    f"[対象={case.target_text}] 年齢検索を廃止したため"
                )
                continue

            active += 1
            issues = []
            period_from = self._parse_date(case.period_from_text, issues)
            period_to = self._parse_date(case.period_to_text, issues)

            tag_names = normalized_tag_names(case.tags)
            tags = list(Tag.objects.filter(name__in=tag_names))
            found_names = {tag.name for tag in tags}
            missing_names = set(tag_names) - found_names
            if missing_names:
                issues.append(f"未登録タグ: {', '.join(sorted(missing_names))}")

            criteria = SearchCriteria(
                period_from=period_from,
                period_to=period_to,
                tag_ids=[tag.id for tag in tags],
            )
            matched_titles = set(
                SearchService.search(criteria)
                .filter(title__in=imported_titles)
                .values_list("title", flat=True)
            )
            actual = tuple(
                sorted(number_by_title[title] for title in matched_titles)
            )
            expected = tuple(sorted(case.expected_numbers))
            success = actual == expected and not issues
            passed += int(success)

            status = "成功" if success else "失敗"
            conditions = []
            if case.period_from_text:
                conditions.append(
                    f"期間={case.period_from_text}〜{case.period_to_text}"
                )
            if case.target_text:
                conditions.append(f"対象={case.target_text}")
            if case.tags:
                conditions.append(f"タグ={','.join(case.tags)}")
            self.stdout.write(
                f"{case.number:02d}. {status} "
                f"[{' / '.join(conditions) or '条件なし'}] "
                f"期待={list(expected)} 実際={list(actual)}"
            )
            for issue in issues:
                self.stdout.write(f"    注意: {issue}")

        summary = (
            f"有効な検索ケース結果: {passed}/{active}件成功"
            f"（年齢条件を含む{skipped}件は対象外）"
        )
        if passed == active:
            self.stdout.write(self.style.SUCCESS(summary))
        else:
            self.stdout.write(self.style.WARNING(summary))
            if options["strict"]:
                raise CommandError(summary)

    @staticmethod
    def _parse_date(value, issues):
        if not value:
            return None
        try:
            return parse_sheet_date(value)
        except ValueError:
            issues.append(f"存在しない日付: {value}")
            # 現在の検索ビューと同じく、不正な日付は未指定として扱う。
            return None
