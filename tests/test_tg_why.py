"""Тесты слоя причина→следствие (decisions.history/search/render_trace) — /tg-why."""

from __future__ import annotations

import decisions


def _events() -> list[dict]:
    return [
        {
            "ts": 100,
            "item_id": "rel",
            "topic": "Релиз v2.3",
            "kind": "decision",
            "statement": "Выкатить v2.3 на прод",
            "why": "регресс пройден, таймаут БД устранён",
            "status": "decided",
            "refs": [105],
        },
        {
            "ts": 50,
            "item_id": "db",
            "topic": "Таймаут БД",
            "kind": "task",
            "statement": "Починить таймаут БД",
            "status": "open",
            "refs": [102],
        },
        {
            "ts": 200,
            "item_id": "rel",
            "effect": "выкачен 5 марта, идёт мониторинг",
            "status": "done",
            "refs": [107],
        },
    ]


def test_history_chronological_and_scoped():
    h = decisions.history(_events(), "rel")
    assert [ev.get("status") for ev in h] == ["decided", "done"]  # по ts: 100, 200
    # только события этой сущности
    assert all(ev["item_id"] == "rel" for ev in h if "item_id" in ev) or len(h) == 2


def test_search_case_insensitive_by_topic_and_statement():
    items = decisions.items_list(decisions.fold(_events()))
    assert {it["item_id"] for it in decisions.search(items, "релиз")} == {"rel"}
    # матч по формулировке, не только теме (уникально для db)
    assert {it["item_id"] for it in decisions.search(items, "починить")} == {"db"}
    assert {it["item_id"] for it in decisions.search(items, "выкатить")} == {"rel"}
    # поиск идёт и по why/effect: 'таймаут' есть и в задаче db, и в причине решения rel
    assert {it["item_id"] for it in decisions.search(items, "таймаут")} == {"db", "rel"}
    assert decisions.search(items, "несуществующее") == []
    assert decisions.search(items, "  ") == []


def test_render_trace_has_cause_effect_timeline_and_refs():
    out = decisions.render_trace(_events(), "rel")
    assert "Почему (причина):" in out
    assert "Следствие (итог):" in out
    assert "Хронология" in out
    assert "[decided]" in out and "[done]" in out
    assert "#105" in out and "#107" in out


def test_render_trace_unknown_item():
    assert "Нет записей" in decisions.render_trace(_events(), "missing")
