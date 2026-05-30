#!/usr/bin/env python3
"""Light-выгрузка дельты сообщений из чатов Telegram через Telethon.

На каждый запуск:
  - для каждой цели (чат, топик) тянет сообщения с id > last_id (только новые);
  - нормализует и раскладывает их по недельным шардам data/<name>/<YYYY-Www>.jsonl
    (ISO-неделя по дате сообщения, UTC; одна дельта на стыке недель пишется
    сразу в два файла — append-only в каждом);
  - обновляет data/state.json (last_id, last_sync);
  - пишет data/<name>/.last_delta.json — манифест последней дельты (включая
    список затронутых недель), чтобы сессия Claude знала, какие именно строки
    новые для суммаризации.

Запуск:  python3 scripts/tg_sync.py            # все цели из config.yaml
         python3 scripts/tg_sync.py --only team-platform
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from telethon import TelegramClient, utils
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageService

import shards

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Конфиг и секреты
# --------------------------------------------------------------------------- #
def load_env(path: Path) -> None:
    """Минимальный .env-загрузчик, чтобы не тащить python-dotenv."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def load_config() -> dict:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    cfg["_data_dir"] = (ROOT / cfg.get("data_dir", "./data")).resolve()
    cfg["_session"] = (ROOT / cfg.get("session", "./secrets/tg")).resolve()
    return cfg


def read_state(data_dir: Path) -> dict:
    f = data_dir / "state.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}


def write_state(data_dir: Path, state: dict) -> None:
    (data_dir / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# Резолв чата по @username / id / названию через список диалогов
# --------------------------------------------------------------------------- #
async def resolve_entity(client: TelegramClient, chat):
    # @username — прямой резолв
    if isinstance(chat, str) and chat.startswith("@"):
        return await client.get_entity(chat)

    # Иначе ищем по списку диалогов (надёжно для чатов, где мы состоим:
    # не нужен access_hash, как при get_entity(positive_id)).
    target_id = chat if isinstance(chat, int) else None
    target_title = chat if isinstance(chat, str) else None
    async for dialog in client.iter_dialogs():
        ent = dialog.entity
        if target_id is not None and getattr(ent, "id", None) == target_id:
            return ent
        if target_title is not None and (dialog.name or "").strip() == target_title.strip():
            return ent
    raise RuntimeError(f"Чат не найден среди диалогов: {chat!r}")


# --------------------------------------------------------------------------- #
# Нормализация сообщения -> компактная запись JSONL
# --------------------------------------------------------------------------- #
def media_kind(msg) -> str | None:
    if msg.media is None:
        return None
    if isinstance(msg.media, MessageMediaPhoto):
        return "photo"
    if isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        mime = getattr(doc, "mime_type", "") or ""
        return mime or "document"
    return type(msg.media).__name__


def normalize(msg, topic) -> dict:
    sender = msg.sender
    rec = {
        "id": msg.id,
        "date": msg.date.astimezone(timezone.utc).isoformat() if msg.date else None,
        "ts": int(msg.date.timestamp()) if msg.date else None,
        "from": utils.get_display_name(sender) if sender else None,
        "from_id": msg.sender_id,
        "topic": topic,
        "reply_to": msg.reply_to_msg_id,
        "edited": msg.edit_date.astimezone(timezone.utc).isoformat() if msg.edit_date else None,
        "fwd": utils.get_display_name(msg.forward.sender)
        if msg.forward and msg.forward.sender
        else (getattr(msg.forward, "from_name", None) if msg.forward else None),
        "media": media_kind(msg),
        "text": msg.raw_text or "",
    }
    return rec


# --------------------------------------------------------------------------- #
# Выгрузка одной цели
# --------------------------------------------------------------------------- #
async def sync_target(client: TelegramClient, cfg: dict, target: dict, state: dict) -> dict:
    name = target["name"]
    topic = target.get("topic")
    data_dir: Path = cfg["_data_dir"]
    out_dir = data_dir / name
    out_dir.mkdir(parents=True, exist_ok=True)

    last_id = state.get(name, {}).get("last_id", 0)
    backfill_days = target.get("backfill_days")
    entity = await resolve_entity(client, target["chat"])

    new_records: list[dict] = []
    if last_id == 0 and backfill_days:
        # Первая загрузка нового чата: ограничиваем окном по дате (newest-first,
        # обрываемся на cutoff — тянем только окно, а не всю историю).
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(backfill_days))
        topic_kw = {"reply_to": topic} if topic is not None else {}
        async for msg in client.iter_messages(entity, **topic_kw):
            if msg.date is not None and msg.date < cutoff:
                break
            if isinstance(msg, MessageService):
                continue
            new_records.append(normalize(msg, topic))
        new_records.reverse()  # привести к возрастанию id
    else:
        # Инкрементальная дельта: только новые (id > last_id), по возрастанию.
        kwargs = {"min_id": last_id, "reverse": True}
        if topic is not None:
            kwargs["reply_to"] = topic
        async for msg in client.iter_messages(entity, **kwargs):
            if msg.id <= last_id or isinstance(msg, MessageService):
                continue
            new_records.append(normalize(msg, topic))

    if new_records:
        weeks = shards.append_by_week(out_dir, new_records)
        new_last = max(r["id"] for r in new_records)
    else:
        weeks = []
        new_last = last_id

    # Манифест дельты — для шага суммаризации в Claude.
    delta = {
        "name": name,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "prev_last_id": last_id,
        "new_last_id": new_last,
        "count": len(new_records),
        "first_id": new_records[0]["id"] if new_records else None,
        "last_id": new_records[-1]["id"] if new_records else None,
        "date_from": new_records[0]["date"] if new_records else None,
        "date_to": new_records[-1]["date"] if new_records else None,
        "weeks": weeks,  # затронутые недельные шарды (имена файлов без .jsonl)
    }
    (out_dir / ".last_delta.json").write_text(
        json.dumps(delta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    state[name] = {"last_id": new_last, "last_sync": delta["synced_at"]}
    return delta


# --------------------------------------------------------------------------- #
async def main() -> int:
    ap = argparse.ArgumentParser(description="Выгрузка дельты сообщений Telegram")
    ap.add_argument("--only", help="Синхронизировать только цель с этим name")
    args = ap.parse_args()

    load_env(ROOT / ".env")
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    phone = os.environ.get("TG_PHONE")
    if not api_id or not api_hash:
        print("ОШИБКА: задайте TG_API_ID и TG_API_HASH в .env (см .env.example)", file=sys.stderr)
        return 2

    cfg = load_config()
    data_dir: Path = cfg["_data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)
    cfg["_session"].parent.mkdir(parents=True, exist_ok=True)

    targets = cfg["targets"]
    if args.only:
        targets = [t for t in targets if t["name"] == args.only]
        if not targets:
            print(f"Цель {args.only!r} не найдена в config.yaml", file=sys.stderr)
            return 2

    state = read_state(data_dir)
    client = TelegramClient(str(cfg["_session"]), int(api_id), api_hash, flood_sleep_threshold=120)
    await client.start(phone=phone)  # интерактивный логин только при первом запуске

    deltas = []
    try:
        for t in targets:
            try:
                delta = await sync_target(client, cfg, t, state)
                deltas.append(delta)
                print(
                    f"[{t['name']}] +{delta['count']} новых "
                    f"(id {delta['first_id']}..{delta['last_id']})"
                )
            except Exception as e:  # noqa: BLE001 — одна упавшая цель не валит остальные
                print(f"[{t['name']}] ОШИБКА: {e}", file=sys.stderr)
            await asyncio.sleep(1)  # бережный rate-limit между целями
    finally:
        write_state(data_dir, state)
        await client.disconnect()

    total = sum(d["count"] for d in deltas)
    print(f"\nИтого новых сообщений: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
