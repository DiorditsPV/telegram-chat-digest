"""Тесты общего модуля недельного шардинга (scripts/shards.py)."""

from __future__ import annotations

from datetime import datetime, timezone

import shards
from conftest import make_rec, write_shard


def _ts(y, m, d, hh=12, mm=0) -> int:
    return int(datetime(y, m, d, hh, mm, tzinfo=timezone.utc).timestamp())


def test_iso_week_basic():
    assert shards.iso_week_of(_ts(2026, 3, 2)) == "2026-W10"  # понедельник W10
    assert shards.iso_week_of(_ts(2026, 3, 9)) == "2026-W11"  # следующий понедельник


def test_iso_week_year_boundary():
    # 2025-12-29 (Пн) принадлежит ISO-неделе 2026-W01, а не 2025-W52.
    assert shards.iso_week_of(_ts(2025, 12, 29)) == "2026-W01"
    # 1 января 2023 (Вс) — это ещё 2022-W52 по ISO.
    assert shards.iso_week_of(_ts(2023, 1, 1)) == "2022-W52"


def test_iso_week_undated():
    assert shards.iso_week_of(None) == "undated"
    assert shards.iso_week_of(0) == "undated"


def test_bucket_by_week_groups_and_uses_undated():
    recs = [
        make_rec(1, _ts(2026, 3, 2)),
        make_rec(2, _ts(2026, 3, 3)),
        make_rec(3, _ts(2026, 3, 9)),
        make_rec(4, None),
    ]
    buckets = shards.bucket_by_week(recs)
    assert set(buckets) == {"2026-W10", "2026-W11", "undated"}
    assert [r["id"] for r in buckets["2026-W10"]] == [1, 2]
    assert [r["id"] for r in buckets["undated"]] == [4]


def test_append_by_week_writes_shards_and_returns_weeks(tmp_path):
    out = tmp_path / "t"
    recs = [make_rec(1, _ts(2026, 3, 2)), make_rec(2, _ts(2026, 3, 9))]
    weeks = shards.append_by_week(out, recs)
    assert weeks == ["2026-W10", "2026-W11"]
    assert shards.read_jsonl(out / "2026-W10.jsonl")[0]["id"] == 1
    # append-only: второй вызов дозаписывает в тот же шард, не затирая.
    shards.append_by_week(out, [make_rec(3, _ts(2026, 3, 3))])
    ids = [r["id"] for r in shards.read_jsonl(out / "2026-W10.jsonl")]
    assert ids == [1, 3]


def test_append_by_week_cross_week_delta(tmp_path):
    # Одна «дельта» на стыке недель распределяется по двум шардам.
    out = tmp_path / "t"
    recs = [make_rec(10, _ts(2026, 3, 8, 23)), make_rec(11, _ts(2026, 3, 9, 1))]
    weeks = shards.append_by_week(out, recs)
    assert weeks == ["2026-W10", "2026-W11"]


def test_shard_paths_sorted(tmp_path):
    d = tmp_path / "t"
    write_shard(d, "2026-W11", [make_rec(3, _ts(2026, 3, 9))])
    write_shard(d, "2026-W10", [make_rec(1, _ts(2026, 3, 2))])
    names = [p.name for p in shards.shard_paths(d)]
    assert names == ["2026-W10.jsonl", "2026-W11.jsonl"]
    assert shards.shard_paths(tmp_path / "missing") == []


def test_read_records_chronological(target_dir):
    recs = shards.read_records(target_dir)
    assert [r["id"] for r in recs] == [101, 102, 103, 104, 105]
