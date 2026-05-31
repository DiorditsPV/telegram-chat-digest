#!/usr/bin/env python3
"""Обзор движения решений/задач за период + что «зависло» (слой отчётов).

Поверх журнала решений (decisions.jsonl, см. decisions.py): за окно [since, now]
классифицирует сущности на новые / обновлённые / завершённые и отдельно выделяет
**зависшие** — open/decided без движения дольше stale_days. Прямо отвечает на
вопрос «что происходит по рабочим задачам и что подвисло».

Чистый stdlib (+ переиспользует decisions для модели событий): без telethon —
тестируется офлайн на ts-фикстурах.
"""

from __future__ import annotations

from datetime import datetime, timezone

import decisions

DAY = 86400
DEFAULT_STALE_DAYS = 14
# Зависшими считаем только то, что ещё в работе.
_ACTIVE = ("open", "decided")


def _fmt_date(ts) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def digest(
    events: list[dict],
    since_ts: int,
    now_ts: int | None = None,
    stale_days: int = DEFAULT_STALE_DAYS,
) -> dict:
    """Свести движение журнала за [since_ts, now_ts] и найти зависшее.

    Категории (могут пересекаться — это разные срезы для обзора):
      new      — сущности, впервые появившиеся в окне (ts_first >= since_ts);
      updated  — имевшие события в окне, но появившиеся раньше;
      done     — со статусом done и движением в окне;
      stale    — open/decided, последнее событие старше stale_days (вне окна тоже).
    """
    folded = decisions.fold(events)
    if now_ts is None:
        now_ts = max((ev.get("ts") or 0) for ev in events) if events else 0

    moved_raw = [
        str(ev["item_id"])
        for ev in events
        if ev.get("item_id") is not None and (ev.get("ts") or 0) >= since_ts
    ]
    moved: list[str] = list(dict.fromkeys(moved_raw))  # уникальные, стабильный порядок

    new_ids: list[str] = []
    updated_ids: list[str] = []
    done_ids: list[str] = []
    for iid in moved:
        it = folded[iid]
        if (it.get("ts_first") or 0) >= since_ts:
            new_ids.append(iid)
        else:
            updated_ids.append(iid)
        if it.get("status") == "done":
            done_ids.append(iid)

    cutoff = now_ts - stale_days * DAY
    stale = [
        it
        for it in folded.values()
        if it.get("status") in _ACTIVE and (it.get("ts_last") or 0) < cutoff
    ]

    def by_recent(ids: list) -> list[dict]:
        return sorted((folded[i] for i in ids), key=lambda it: -(it.get("ts_last") or 0))

    return {
        "since_ts": since_ts,
        "now_ts": now_ts,
        "stale_days": stale_days,
        "new": by_recent(new_ids),
        "updated": by_recent(updated_ids),
        "done": by_recent(done_ids),
        "stale": sorted(stale, key=lambda it: it.get("ts_last") or 0),
    }


def _line(it: dict) -> str:
    status = it.get("status") or "open"
    topic = it.get("topic") or "(без темы)"
    refs = " ".join(f"#{r}" for r in it.get("refs") or [])
    line = f"- **[{status}]** {it.get('statement') or it['item_id']} · _{topic}_"
    if refs:
        line += f" ({refs})"
    return line


def render_digest(result: dict, title: str = "Дайджест решений и задач") -> str:
    """Markdown-обзор: что нового/обновилось/завершено за период и что зависло."""
    period = f"{_fmt_date(result.get('since_ts'))} … {_fmt_date(result.get('now_ts'))}"
    lines = [f"# {title}", "", f"_Период: {period}_", ""]

    sections = [
        ("Новые", result.get("new") or []),
        ("Обновлённые", result.get("updated") or []),
        ("Завершено", result.get("done") or []),
    ]
    any_movement = False
    for name, items in sections:
        if not items:
            continue
        any_movement = True
        lines.append(f"## {name} ({len(items)})")
        lines += [_line(it) for it in items]
        lines.append("")
    if not any_movement:
        lines += ["_За период движения нет._", ""]

    stale = result.get("stale") or []
    if stale:
        now_ts = result.get("now_ts") or 0
        lines.append(f"## Зависло — нет движения > {result.get('stale_days')} дн. ({len(stale)})")
        for it in stale:
            days = (now_ts - (it.get("ts_last") or 0)) // DAY
            lines.append(f"{_line(it)} — {days} дн. без движения")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
