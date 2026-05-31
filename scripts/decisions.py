#!/usr/bin/env python3
"""Лёгкий журнал решений/задач по темам (слой данных «Решения и темы»).

Цель проекта — легковесно понимать суть рабочих задач и причину→следствие
принятых решений по темам. `context.md` ведёт это прозой; здесь — структурный,
запрашиваемый срез.

`data/<name>/decisions.jsonl` — append-only event-log (как и шарды). Одно
событие = факт/обновление о решении или задаче; события с одним `item_id`
сворачиваются (`fold`) в текущее состояние, а их последовательность во времени
даёт цепочку причина→следствие (см. tg_why.history).

Чистый stdlib (+ переиспользует shards для чтения JSONL): «интеллект» (выделение
решений из переписки) — у сессии Claude в /tg-sync, как и для context.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import shards

KINDS = ("decision", "task")
STATUSES = ("open", "decided", "done", "reversed")
# Порядок вывода статусов на доске: сначала то, что требует внимания.
_STATUS_ORDER = {"open": 0, "decided": 1, "done": 2, "reversed": 3}
# Поля, которые при свёртке берём «последним непустым».
_MERGE_FIELDS = ("topic", "kind", "statement", "why", "effect", "status", "note")


def validate_event(ev: dict) -> list[str]:
    """Вернуть список ошибок события (пустой = валидно)."""
    errors: list[str] = []
    if not isinstance(ev, dict):
        return ["событие не является объектом"]
    if not ev.get("item_id"):
        errors.append("нет обязательного поля item_id")
    kind = ev.get("kind")
    if kind is not None and kind not in KINDS:
        errors.append(f"kind={kind!r} не из {KINDS}")
    status = ev.get("status")
    if status is not None and status not in STATUSES:
        errors.append(f"status={status!r} не из {STATUSES}")
    refs = ev.get("refs")
    if refs is not None and not isinstance(refs, list):
        errors.append("refs должно быть списком id сообщений")
    return errors


def load(path: Path) -> list[dict]:
    """Прочитать event-log решений (JSONL). Нет файла → пустой список."""
    if not Path(path).exists():
        return []
    return shards.read_jsonl(Path(path))


def _event_sort_key(item: tuple[int, dict]):
    idx, ev = item
    # Стабильно: по ts (события без ts — по порядку в файле), затем по позиции.
    return (ev.get("ts") or 0, idx)


def fold(events: list[dict]) -> dict[str, dict]:
    """Свернуть события в текущее состояние сущностей по `item_id`.

    Поля из `_MERGE_FIELDS` берутся последними непустыми; `refs` — объединение
    (отсортированное, уникальное); трекаются `ts_first`/`ts_last` и `events`.
    """
    items: dict[str, dict] = {}
    for _, ev in sorted(enumerate(events), key=_event_sort_key):
        iid = ev.get("item_id")
        if not iid:
            continue
        cur = items.get(iid)
        if cur is None:
            cur = {"item_id": iid, "refs": [], "events": 0, "ts_first": None, "ts_last": None}
            items[iid] = cur
        for f in _MERGE_FIELDS:
            val = ev.get(f)
            if val not in (None, ""):
                cur[f] = val
        for ref in ev.get("refs") or []:
            if ref not in cur["refs"]:
                cur["refs"].append(ref)
        ts = ev.get("ts")
        if ts is not None:
            if cur["ts_first"] is None:
                cur["ts_first"] = ts
            cur["ts_last"] = ts
        cur["events"] += 1
    for cur in items.values():
        cur["refs"].sort()
    return items


def items_list(folded: dict[str, dict]) -> list[dict]:
    """Список сущностей, упорядоченный по теме, затем по времени появления."""
    return sorted(
        folded.values(),
        key=lambda it: (it.get("topic") or "~", it.get("ts_first") or 0, it["item_id"]),
    )


def by_topic(items: list[dict]) -> dict[str, list[dict]]:
    """Сгруппировать сущности по теме (порядок тем — по первому появлению)."""
    groups: dict[str, list[dict]] = {}
    for it in items:
        groups.setdefault(it.get("topic") or "(без темы)", []).append(it)
    return groups


def filter_status(items: list[dict], *statuses: str) -> list[dict]:
    """Оставить сущности с указанными статусами."""
    wanted = set(statuses)
    return [it for it in items if it.get("status") in wanted]


def append_event(path: Path, ev: dict) -> None:
    """Дозаписать валидное событие в журнал (append-only)."""
    errors = validate_event(ev)
    if errors:
        raise ValueError("невалидное событие: " + "; ".join(errors))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def _fmt_refs(refs: list) -> str:
    return " ".join(f"#{r}" for r in refs) if refs else ""


def _item_line(it: dict) -> str:
    status = it.get("status") or "open"
    parts = [f"- **[{status}]** {it.get('statement') or it['item_id']}"]
    if it.get("why"):
        parts.append(f"_почему:_ {it['why']}")
    if it.get("effect"):
        parts.append(f"_итог:_ {it['effect']}")
    refs = _fmt_refs(it.get("refs") or [])
    if refs:
        parts.append(f"({refs})")
    return " · ".join(parts)


def render_board(items: list[dict], title: str = "Доска решений и задач") -> str:
    """Markdown-доска: по темам — задачи/решения и статусы (суть задач с одного взгляда)."""
    lines = [f"# {title}", "", "_Сгенерировано scripts/decisions.py из decisions.jsonl_", ""]
    groups = by_topic(items)
    if not groups:
        lines.append("_Журнал пуст._")
        return "\n".join(lines) + "\n"
    for topic, its in groups.items():
        lines.append(f"## {topic}")
        for it in sorted(
            its, key=lambda i: (_STATUS_ORDER.get(i.get("status") or "", 9), i["item_id"])
        ):
            lines.append(_item_line(it))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
