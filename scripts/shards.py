#!/usr/bin/env python3
"""Общий модуль недельного шардинга сообщений (источник истины).

Раньше логику ISO-недели и бакетизации по неделям дублировали tg_sync.py,
import_export.py и migrate_to_weekly.py (инвариант: «менять согласованно»).
Теперь она здесь — единожды, покрыта тестами и переиспользуется всеми скриптами
и фичами аналитики.

Чистый stdlib: НЕ импортирует telethon/yaml, чтобы тесты и аналитика работали
без установленного Telethon. Формат шарда — append-only JSONL, имя `YYYY-Www`
по ISO-неделе даты сообщения (UTC); сообщения без даты идут в шард `undated`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

UNDATED = "undated"


def iso_week_of(ts: int | None) -> str:
    """ISO-неделя UTC в формате 'YYYY-Www' (имя недельного шарда).

    Сообщения без даты (`ts` пуст) складываем в отдельный шард 'undated',
    чтобы не терять.
    """
    if not ts:
        return UNDATED
    y, w, _ = datetime.fromtimestamp(ts, tz=timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


def bucket_by_week(records: Iterable[dict]) -> dict[str, list[dict]]:
    """Разложить записи по неделям (ключ — имя шарда из `iso_week_of`)."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        buckets[iso_week_of(rec.get("ts"))].append(rec)
    return buckets


def append_by_week(out_dir: Path, records: Iterable[dict], mode: str = "a") -> list[str]:
    """Записать записи в недельные шарды out_dir/<YYYY-Www>.jsonl.

    По умолчанию дозапись (`mode="a"`, append-only — источник истины). Возвращает
    отсортированный список затронутых недель. Одна дельта на стыке недель
    естественно попадает в разные шарды (бакетизация по дате каждой записи).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    buckets = bucket_by_week(records)
    for week, recs in sorted(buckets.items()):
        with (out_dir / f"{week}.jsonl").open(mode, encoding="utf-8") as f:
            for rec in recs:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return sorted(buckets)


def iter_jsonl(path: Path) -> Iterator[dict]:
    """Лениво прочитать один JSONL-шард, пропуская пустые строки."""
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_jsonl(path: Path) -> list[dict]:
    """Прочитать один JSONL-шард целиком."""
    return list(iter_jsonl(path))


def shard_paths(target_dir: Path) -> list[Path]:
    """Отсортированный список недельных шардов цели (`*.jsonl`).

    Имена недель `YYYY-Www` сортируются лексикографически = хронологически;
    `undated` оказывается в конце (буква 'u' > цифр), что разумно.
    """
    if not target_dir.exists():
        return []
    return sorted(target_dir.glob("*.jsonl"))


def read_records(target_dir: Path) -> list[dict]:
    """Прочитать все сообщения цели из всех недельных шардов.

    Сортировка по (`ts`, `id`) — устойчивый хронологический порядок;
    записи без `ts` (undated) идут первыми, но внутри стабилизируются по `id`.
    """
    records: list[dict] = []
    for path in shard_paths(target_dir):
        records.extend(iter_jsonl(path))
    records.sort(key=lambda r: (r.get("ts") or 0, r.get("id") or 0))
    return records
