"""純粋ロジックのテスト。DBに依存しないunittest。"""
import unittest
from datetime import date

from search.criteria import SearchCriteria
from search.logic import is_criteria_empty, period_overlaps


class PeriodOverlapsTests(unittest.TestCase):
    def test_both_unbounded_always_overlap(self):
        self.assertTrue(period_overlaps(None, None, None, None))

    def test_one_side_fully_unbounded_overlaps_regardless_of_other(self):
        self.assertTrue(
            period_overlaps(None, None, date(2026, 1, 1), date(2026, 1, 31))
        )
        self.assertTrue(
            period_overlaps(date(2026, 1, 1), date(2026, 1, 31), None, None)
        )

    def test_overlapping_ranges(self):
        self.assertTrue(
            period_overlaps(
                date(2026, 1, 1), date(2026, 1, 31),
                date(2026, 1, 15), date(2026, 2, 15),
            )
        )

    def test_touching_boundaries_count_as_overlap(self):
        self.assertTrue(
            period_overlaps(
                date(2026, 1, 1), date(2026, 1, 10),
                date(2026, 1, 10), date(2026, 1, 20),
            )
        )

    def test_non_overlapping_ranges(self):
        self.assertFalse(
            period_overlaps(
                date(2026, 1, 1), date(2026, 1, 10),
                date(2026, 2, 1), date(2026, 2, 10),
            )
        )

    def test_open_ended_boundary_only_blocks_when_clearly_outside(self):
        # 検索側period_toのみ指定 -> それより後に始まるイベントは重ならない
        self.assertFalse(
            period_overlaps(None, date(2026, 1, 10), date(2026, 1, 11), None)
        )
        self.assertTrue(
            period_overlaps(None, date(2026, 1, 10), date(2026, 1, 9), None)
        )


class IsCriteriaEmptyTests(unittest.TestCase):
    def test_default_criteria_is_empty(self):
        self.assertTrue(is_criteria_empty(SearchCriteria()))

    def test_keyword_makes_non_empty(self):
        self.assertFalse(is_criteria_empty(SearchCriteria(keyword="花火")))

    def test_location_makes_non_empty(self):
        self.assertFalse(is_criteria_empty(SearchCriteria(location="東京")))

    def test_period_from_makes_non_empty(self):
        self.assertFalse(
            is_criteria_empty(SearchCriteria(period_from=date(2026, 1, 1)))
        )

    def test_period_to_makes_non_empty(self):
        self.assertFalse(
            is_criteria_empty(SearchCriteria(period_to=date(2026, 1, 1)))
        )

    def test_tags_makes_non_empty(self):
        self.assertFalse(is_criteria_empty(SearchCriteria(tag_ids=[1])))


if __name__ == "__main__":
    unittest.main()
