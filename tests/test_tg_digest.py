"""Тесты обзора движения решений/задач (scripts/tg_digest.py) — /tg-digest."""

from __future__ import annotations

import tg_digest

DAY = 86400
NOW = 1_000_000 * DAY  # фиксированное «сейчас» для детерминизма


def _events() -> list[dict]:
    return [
        # appeared and finished inside the last week -> new + done
        {
            "ts": NOW - 2 * DAY,
            "item_id": "fresh",
            "topic": "A",
            "statement": "Свежая задача",
            "status": "open",
            "refs": [1],
        },
        {
            "ts": NOW - 1 * DAY,
            "item_id": "fresh",
            "effect": "сделано",
            "status": "done",
            "refs": [2],
        },
        # old item, but moved within window -> updated
        {
            "ts": NOW - 40 * DAY,
            "item_id": "old-moved",
            "topic": "B",
            "statement": "Старое, но двигалось",
            "status": "open",
            "refs": [3],
        },
        {"ts": NOW - 3 * DAY, "item_id": "old-moved", "status": "decided", "refs": [4]},
        # open, no movement for ~30 days -> stale (and NOT in window)
        {
            "ts": NOW - 30 * DAY,
            "item_id": "stuck",
            "topic": "C",
            "statement": "Подвисло",
            "status": "open",
            "refs": [5],
        },
    ]


def test_digest_classifies_window_and_stale():
    res = tg_digest.digest(_events(), since_ts=NOW - 7 * DAY, now_ts=NOW, stale_days=14)
    assert [it["item_id"] for it in res["new"]] == ["fresh"]
    assert [it["item_id"] for it in res["updated"]] == ["old-moved"]
    assert [it["item_id"] for it in res["done"]] == ["fresh"]
    # stuck: open, last event 30d ago > 14d; old-moved last moved 3d ago (not stale);
    # fresh is done (not active). So only 'stuck' is stale.
    assert [it["item_id"] for it in res["stale"]] == ["stuck"]


def test_digest_now_defaults_to_latest_event():
    res = tg_digest.digest(_events(), since_ts=NOW - 7 * DAY)
    assert res["now_ts"] == NOW - 1 * DAY  # самое позднее событие


def test_digest_empty():
    res = tg_digest.digest([], since_ts=0, now_ts=DAY)
    assert res["new"] == [] and res["stale"] == []


def test_render_digest_sections_and_refs():
    res = tg_digest.digest(_events(), since_ts=NOW - 7 * DAY, now_ts=NOW, stale_days=14)
    out = tg_digest.render_digest(res)
    assert "## Новые" in out
    assert "## Завершено" in out
    assert "Зависло" in out
    assert "#2" in out and "#5" in out
    assert "дн. без движения" in out


def test_render_digest_no_movement():
    # окно в будущем -> ничего не двигалось, но 'stuck' всё равно зависшее
    res = tg_digest.digest(_events(), since_ts=NOW + DAY, now_ts=NOW + 2 * DAY, stale_days=14)
    out = tg_digest.render_digest(res)
    assert "движения нет" in out
