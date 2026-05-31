#!/usr/bin/env python3
"""Разовая миграция старого формата хранения в недельные шарды.

Раньше сообщения каждой цели лежали в одном растущем файле data/<name>/raw.jsonl.
Теперь — по недельным шардам data/<name>/<YYYY-Www>.jsonl (ISO-неделя по дате
сообщения, UTC). Скрипт разрезает каждый raw.jsonl по неделям и сохраняет
оригинал как raw.jsonl.migrated (НЕ удаляет — на случай отката).

Идемпотентен: если raw.jsonl уже нет (или есть только .migrated) — цель пропускается.

Запуск:  python3 scripts/migrate_to_weekly.py              # все цели в data/
         python3 scripts/migrate_to_weekly.py --only team-platform
         python3 scripts/migrate_to_weekly.py --dry-run     # только показать план
"""

from __future__ import annotations

import argparse
from pathlib import Path

import shards

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def migrate_target(target_dir: Path, dry_run: bool) -> bool:
    raw = target_dir / "raw.jsonl"
    if not raw.exists():
        return False

    records = shards.read_jsonl(raw)
    records.sort(key=lambda r: r.get("id", 0))

    buckets = shards.bucket_by_week(records)
    plan = ", ".join(f"{w}:{len(rs)}" for w, rs in sorted(buckets.items()))
    print(f"[{target_dir.name}] {len(records)} сообщ. -> {len(buckets)} недель ({plan})")
    if dry_run:
        return True

    # append, чтобы не затереть шарды, если миграцию запустили повторно частично
    shards.append_by_week(target_dir, records, mode="a")
    raw.rename(target_dir / "raw.jsonl.migrated")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Миграция raw.jsonl -> недельные шарды")
    ap.add_argument("--only", help="мигрировать только цель с этим name")
    ap.add_argument("--dry-run", action="store_true", help="показать план без записи")
    args = ap.parse_args()

    if not DATA.exists():
        print(f"Нет каталога данных: {DATA}")
        return 0

    targets = [d for d in sorted(DATA.iterdir()) if d.is_dir()]
    if args.only:
        targets = [d for d in targets if d.name == args.only]

    migrated = sum(migrate_target(d, args.dry_run) for d in targets)
    if not migrated:
        print("Нечего мигрировать (raw.jsonl не найдены).")
    elif not args.dry_run:
        print(
            f"\nГотово. Мигрировано целей: {migrated}. Оригиналы сохранены как raw.jsonl.migrated."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
