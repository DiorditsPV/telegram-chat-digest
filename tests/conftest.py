"""Общие фикстуры для тестов фич аналитики над недельными шардами.

Тесты не ходят в сеть и не импортируют telethon: работают с синтетическими
JSONL-шардами во временном каталоге (формат — как в examples/team-platform/).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


def make_rec(id: int, ts: int | None, text: str = "", **over) -> dict:
    """Собрать запись сообщения в формате шардов (схема — см. AGENTS.md / README)."""
    date = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts is not None else None
    rec = {
        "id": id,
        "date": date,
        "ts": ts,
        "from": "Alice Carter",
        "from_id": 111000001,
        "topic": 12,
        "reply_to": None,
        "edited": None,
        "fwd": None,
        "media": None,
        "text": text,
    }
    rec.update(over)
    return rec


def write_shard(dir_: Path, week: str, records: list[dict]) -> Path:
    """Записать список записей в шард dir_/<week>.jsonl (append-only)."""
    dir_.mkdir(parents=True, exist_ok=True)
    shard = dir_ / f"{week}.jsonl"
    with shard.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return shard


# Эпохи для двух соседних ISO-недель (UTC), чтобы тесты были детерминированы.
TS_W10 = int(datetime(2026, 3, 2, 9, 14, tzinfo=timezone.utc).timestamp())  # 2026-W10 (Пн)
TS_W10_B = int(datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc).timestamp())  # 2026-W10
TS_W11 = int(datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc).timestamp())  # 2026-W11 (Пн)


@pytest.fixture
def target_dir(tmp_path: Path) -> Path:
    """Каталог одной цели data/<name>/ с двумя недельными шардами и разными авторами."""
    d = tmp_path / "team-platform"
    write_shard(
        d,
        "2026-W10",
        [
            make_rec(101, TS_W10, "Привет, стейджинг обновили", **{"from": "Alice Carter"}),
            make_rec(102, TS_W10_B, "Запускаю прогон", reply_to=101, **{"from": "Bob Dev"}),
            make_rec(103, TS_W10_B, "фото отчёта", media="photo", **{"from": "Alice Carter"}),
        ],
    )
    write_shard(
        d,
        "2026-W11",
        [
            make_rec(104, TS_W11, "Прогон зелёный", reply_to=102, **{"from": "Bob Dev"}),
            make_rec(105, TS_W11, "Спасибо!", reply_to=104, **{"from": "Carol QA"}),
        ],
    )
    return d
