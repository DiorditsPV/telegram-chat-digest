#!/usr/bin/env python3
"""Сидинг raw.jsonl из ручного экспорта Telegram Desktop (result.json).

Конвертирует существующий экспорт в наш формат и проставляет стартовый last_id
в state.json — чтобы первая выгрузка через tg_sync.py тянула только новую дельту.

Запуск:
    python3 scripts/import_export.py --export "ChatExport_2026-01-15 (1)" \
        --name team-platform --topic 12
    python3 scripts/import_export.py --export "ChatExport_2026-01-15" \
        --name team-ops
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def iso_week_of(ts: int | None) -> str:
    """ISO-неделя UTC 'YYYY-Www' — имя недельного шарда (см. tg_sync.py)."""
    if not ts:
        return "undated"
    y, w, _ = datetime.fromtimestamp(ts, tz=timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


def render_text(text) -> str:
    """text в экспорте — строка или список из строк и {type,text}-словарей."""
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        parts = []
        for p in text:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                parts.append(p.get("text", ""))
        return "".join(parts)
    return ""


def parse_from_id(raw) -> object:
    if not raw:
        return None
    s = str(raw)
    for prefix in ("user", "channel", "chat"):
        if s.startswith(prefix) and s[len(prefix):].isdigit():
            return int(s[len(prefix):])
    return raw


def media_kind(m: dict) -> str | None:
    if "photo" in m:
        return "photo"
    if "file" in m:
        return m.get("media_type") or "document"
    return None


def normalize(m: dict, topic) -> dict:
    return {
        "id": m["id"],
        "date": m.get("date"),
        "ts": int(m["date_unixtime"]) if m.get("date_unixtime") else None,
        "from": m.get("from"),
        "from_id": parse_from_id(m.get("from_id")),
        "topic": topic,
        "reply_to": m.get("reply_to_message_id"),
        "edited": m.get("edited"),
        "fwd": m.get("forwarded_from"),
        "media": media_kind(m),
        "text": render_text(m.get("text", "")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True, help="папка экспорта с result.json")
    ap.add_argument("--name", required=True, help="имя цели (slug) из config.yaml")
    ap.add_argument("--topic", type=int, default=None)
    args = ap.parse_args()

    src = (ROOT / args.export / "result.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    msgs = [m for m in data["messages"] if m.get("type") == "message"]

    out_dir = DATA / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = list(out_dir.glob("*.jsonl"))
    if existing:
        print(f"ОШИБКА: в {out_dir} уже есть шарды ({len(existing)} шт.) — "
              f"не перетираю. Удалите вручную при необходимости.")
        return 1

    records = [normalize(m, args.topic) for m in msgs]
    records.sort(key=lambda r: r["id"])

    # Раскладываем по недельным шардам (ISO-неделя по дате сообщения, UTC).
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        buckets[iso_week_of(r.get("ts"))].append(r)
    for week, recs in sorted(buckets.items()):
        with (out_dir / f"{week}.jsonl").open("w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    last_id = max(r["id"] for r in records)
    state_f = DATA / "state.json"
    state = json.loads(state_f.read_text(encoding="utf-8")) if state_f.exists() else {}
    state[args.name] = {
        "last_id": last_id,
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "seeded_from_export": args.export,
    }
    state_f.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{args.name}] импортировано {len(records)} сообщений, "
          f"id {records[0]['id']}..{last_id} (chat: {data.get('name')!r})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
