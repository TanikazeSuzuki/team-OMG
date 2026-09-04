"""検索条件を表す純粋なデータ構造。

DBやDjangoに依存しない、モデル非依存の純粋なロジックの一部として、SearchServiceや
MatchServiceの双方から共通の入力形式として使う。
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Optional


@dataclass
class SearchCriteria:
    """検索条件。全フィールドは任意（空文字列またはNoneは無制限を意味する）。"""

    keyword: str = ""
    location: str = ""
    period_from: Optional[date] = None
    period_to: Optional[date] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    tag_ids: Iterable[int] = field(default_factory=tuple)
