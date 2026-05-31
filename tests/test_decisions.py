"""Тесты лёгкого журнала решений/задач (scripts/decisions.py)."""

from __future__ import annotations

import decisions
import pytest


def _events() -> list[dict]:
    # Две сущности, каждая с двумя событиями (open/decided -> done) + объединение refs.
    return [
        {
            "ts": 100,
            "item_id": "rel",
            "topic": "Релиз",
            "kind": "decision",
            "statement": "Выкатить v2.3",
            "why": "регресс пройден",
            "status": "decided",
            "refs": [105],
        },
        {
            "ts": 90,
            "item_id": "bug",
            "topic": "Баг",
            "kind": "task",
            "statement": "Починить пагинацию",
            "status": "open",
            "refs": [106],
        },
        {
            "ts": 200,
            "item_id": "rel",
            "topic": "Релиз",
            "kind": "decision",
            "effect": "выкачен на прод",
            "status": "done",
            "refs": [107, 105],
        },
    ]


def test_fold_merges_by_item_id():
    folded = decisions.fold(_events())
    assert set(folded) == {"rel", "bug"}
    rel = folded["rel"]
    # status = последний по времени; поля сохраняются с разных событий.
    assert rel["status"] == "done"
    assert rel["statement"] == "Выкатить v2.3"
    assert rel["why"] == "регресс пройден"
    assert rel["effect"] == "выкачен на прод"
    # refs объединены, уникальны, отсортированы.
    assert rel["refs"] == [105, 107]
    assert rel["events"] == 2
    assert rel["ts_first"] == 100 and rel["ts_last"] == 200


def test_fold_ignores_events_without_item_id():
    folded = decisions.fold([{"ts": 1, "statement": "no id"}])
    assert folded == {}


def test_items_list_ordered_by_topic_then_time():
    items = decisions.items_list(decisions.fold(_events()))
    assert [it["item_id"] for it in items] == ["bug", "rel"]  # 'Баг' < 'Релиз'


def test_by_topic_groups():
    items = decisions.items_list(decisions.fold(_events()))
    groups = decisions.by_topic(items)
    assert set(groups) == {"Баг", "Релиз"}
    assert groups["Релиз"][0]["item_id"] == "rel"


def test_filter_status():
    items = decisions.items_list(decisions.fold(_events()))
    assert [it["item_id"] for it in decisions.filter_status(items, "open")] == ["bug"]
    assert {it["item_id"] for it in decisions.filter_status(items, "open", "done")} == {
        "bug",
        "rel",
    }


def test_validate_event():
    assert decisions.validate_event({"item_id": "x", "kind": "task", "status": "open"}) == []
    assert decisions.validate_event({"kind": "task"})  # нет item_id
    assert decisions.validate_event({"item_id": "x", "kind": "bogus"})
    assert decisions.validate_event({"item_id": "x", "status": "bogus"})
    assert decisions.validate_event({"item_id": "x", "refs": "nope"})


def test_append_event_roundtrip(tmp_path):
    path = tmp_path / "team" / "decisions.jsonl"
    decisions.append_event(path, {"item_id": "a", "topic": "T", "status": "open", "refs": [1]})
    decisions.append_event(path, {"item_id": "a", "status": "done", "refs": [2]})
    items = decisions.items_list(decisions.fold(decisions.load(path)))
    assert len(items) == 1
    assert items[0]["status"] == "done"
    assert items[0]["refs"] == [1, 2]


def test_append_event_rejects_invalid(tmp_path):
    with pytest.raises(ValueError):
        decisions.append_event(tmp_path / "d.jsonl", {"topic": "T"})  # нет item_id


def test_load_missing_returns_empty(tmp_path):
    assert decisions.load(tmp_path / "nope.jsonl") == []


def test_render_board_contains_topics_statuses_refs():
    items = decisions.items_list(decisions.fold(_events()))
    board = decisions.render_board(items)
    assert "## Релиз" in board and "## Баг" in board
    assert "[done]" in board and "[open]" in board
    assert "#105" in board and "#107" in board
    assert "_почему:_" in board and "_итог:_" in board


def test_render_board_empty():
    assert "Журнал пуст" in decisions.render_board([])
