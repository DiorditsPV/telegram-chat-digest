"""Тесты оси ответственности (decisions.by_owner/for_owner, owner на доске) — /tg-mine."""

from __future__ import annotations

import decisions


def _events() -> list[dict]:
    return [
        {
            "ts": 10,
            "item_id": "rel",
            "topic": "Релиз",
            "statement": "Выкатить v2.3",
            "owner": "Alice Carter",
            "status": "decided",
            "refs": [105],
        },
        {
            "ts": 20,
            "item_id": "db",
            "topic": "БД",
            "statement": "Починить таймаут",
            "owner": "Bob Dev",
            "status": "open",
            "refs": [102],
        },
        {
            "ts": 30,
            "item_id": "doc",
            "topic": "Доки",
            "statement": "Обновить ченджлог",
            "status": "open",
            "refs": [108],
        },  # без owner
    ]


def _items():
    return decisions.items_list(decisions.fold(_events()))


def test_for_owner_case_insensitive_substring():
    assert {it["item_id"] for it in decisions.for_owner(_items(), "alice")} == {"rel"}
    assert {it["item_id"] for it in decisions.for_owner(_items(), "Bob Dev")} == {"db"}
    # частичный матч по фамилии
    assert {it["item_id"] for it in decisions.for_owner(_items(), "carter")} == {"rel"}


def test_for_owner_no_match_and_empty():
    assert decisions.for_owner(_items(), "Кто-то") == []
    assert decisions.for_owner(_items(), "") == []
    assert decisions.for_owner(_items(), "   ") == []


def test_by_owner_groups_including_unassigned():
    groups = decisions.by_owner(_items())
    assert groups["Alice Carter"][0]["item_id"] == "rel"
    assert groups["Bob Dev"][0]["item_id"] == "db"
    assert groups["(не назначено)"][0]["item_id"] == "doc"


def test_owner_shown_on_board():
    board = decisions.render_board(_items())
    assert "_отв.:_ Alice Carter" in board
    assert "_отв.:_ Bob Dev" in board


def test_fold_keeps_owner():
    folded = decisions.fold(_events())
    assert folded["rel"]["owner"] == "Alice Carter"
    assert "owner" not in folded["doc"]  # не назначен — поля нет
