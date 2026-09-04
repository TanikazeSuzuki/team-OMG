"""検索・マッチング判定に使う純粋なロジック。

DBやDjangoモデルに依存しない、モデル非依存の純粋なロジック。同じ判定基準を
SearchService（SQL/QuerySet側）とMatchService（Python側）の両方で
一致させるための唯一の情報源として扱う。
"""


def _ranges_overlap(low1, high1, low2, high2):
    """2つの範囲が重なるかどうかを判定する共通ロジック。

    各境界はNoneの場合、その方向に無制限であることを表す。
    境界が一致するだけ（接する）場合も重なりとみなす。
    """
    if low1 is not None and high2 is not None and low1 > high2:
        return False
    if low2 is not None and high1 is not None and low2 > high1:
        return False
    return True


def period_overlaps(period1_from, period1_to, period2_from, period2_to):
    """2つの期間が重なるかどうかを判定する。

    境界(from/to)がNoneの場合はその方向に無制限として扱う。
    """
    return _ranges_overlap(period1_from, period1_to, period2_from, period2_to)


def age_ranges_overlap(age1_min, age1_max, age2_min, age2_max):
    """2つの対象年齢の範囲が重なるかどうかを判定する。

    境界(min/max)がNoneの場合は無制限（下限なし・上限なし）として扱う。
    """
    return _ranges_overlap(age1_min, age1_max, age2_min, age2_max)


def is_criteria_empty(criteria):
    """検索条件が実質的に空（絞り込みなし）かどうかを判定する。"""
    return (
        not criteria.keyword
        and not criteria.location
        and criteria.period_from is None
        and criteria.period_to is None
        and criteria.age_min is None
        and criteria.age_max is None
        and not list(criteria.tag_ids)
    )
