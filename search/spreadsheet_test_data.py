"""Googleスプレッドシート由来のイベント・検索ケースを読み取る。"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parent / "testdata" / "spreadsheet_test_data.csv"

TAG_ALIASES = {
    "事前登録": "事前",
    "国際文化": "国際",
}


@dataclass(frozen=True)
class EventSpec:
    number: int
    title: str
    start_date: date
    end_date: date
    time_text: str
    target_text: str
    fee_text: str
    location: str
    summary: str
    url: str
    tags: tuple[str, ...]
    provisional_tags: tuple[str, ...]


@dataclass(frozen=True)
class SearchCase:
    number: int
    period_from_text: str
    period_to_text: str
    target_text: str
    tags: tuple[str, ...]
    expected_numbers: tuple[int, ...]


def split_terms(value):
    return tuple(term.strip() for term in re.split(r"[、，,]", value or "") if term.strip())


def parse_sheet_date(value):
    return date.fromisoformat(value.strip().replace("/", "-"))


def parse_age_range(target_text):
    """数値で明示された年齢だけをEventのmin_age/max_ageへ移す。"""
    range_match = re.search(r"(\d+)歳[〜～~-](\d+)歳", target_text)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))

    lower_match = re.search(r"(\d+)歳以上", target_text)
    if lower_match:
        return int(lower_match.group(1)), None

    decade_match = re.search(r"(\d+)代[〜～~-]", target_text)
    if decade_match:
        return int(decade_match.group(1)), None

    return None, None


def build_description(spec):
    """専用モデル項目がない列も失わず、説明文へ読みやすく保存する。"""
    details = [
        spec.summary,
        "",
        f"テストデータ番号: {spec.number}",
        f"開催時間: {spec.time_text}",
        f"ターゲット年齢: {spec.target_text}",
        f"参加費用: {spec.fee_text}",
    ]
    if spec.provisional_tags:
        details.append(f"仮タグ: {'、'.join(spec.provisional_tags)}")
    return "\n".join(details)


def load_event_specs():
    specs = []
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            number_text = (row.get("列 1") or "").strip()
            if not number_text.isdigit():
                continue
            specs.append(
                EventSpec(
                    number=int(number_text),
                    title=(row.get("イベント名") or "").strip(),
                    start_date=parse_sheet_date(row.get("開始期間") or ""),
                    end_date=parse_sheet_date(row.get("終了期間") or ""),
                    time_text=(row.get("時間") or "").strip(),
                    target_text=(row.get("ターゲット年齢") or "").strip(),
                    fee_text=(row.get("参加費用") or "").strip(),
                    location=(row.get("位置") or "").strip(),
                    summary=(row.get("概要") or "").strip(),
                    url=(row.get("URL") or "").strip(),
                    tags=split_terms(row.get("タグ")),
                    provisional_tags=split_terms(row.get("タグ(仮)")),
                )
            )
    return tuple(specs)


def load_search_cases():
    rows_by_label = {}
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.reader(source):
            if row and row[0] in {"期間", "ターゲット年齢", "タグ", "イベント番号"}:
                rows_by_label[row[0]] = row

    expected_row = rows_by_label["イベント番号"]
    cases = []
    for column_index, expected_text in enumerate(expected_row[1:], start=1):
        if not expected_text.strip():
            continue

        period_text = _cell(rows_by_label["期間"], column_index)
        if "~" in period_text:
            period_from_text, period_to_text = period_text.split("~", maxsplit=1)
        else:
            period_from_text = period_to_text = ""

        cases.append(
            SearchCase(
                number=len(cases) + 1,
                period_from_text=period_from_text,
                period_to_text=period_to_text,
                target_text=_cell(rows_by_label["ターゲット年齢"], column_index),
                tags=split_terms(_cell(rows_by_label["タグ"], column_index)),
                expected_numbers=tuple(
                    int(number) for number in split_terms(expected_text)
                ),
            )
        )
    return tuple(cases)


def normalized_tag_names(names):
    return tuple(TAG_ALIASES.get(name, name) for name in names)


def _cell(row, index):
    if index >= len(row):
        return ""
    return row[index].strip()
