#!/usr/bin/env python3
"""Light-обзор всех групп/супергрупп, активных за последние N дней.

Окно N дней задаётся флагом --days (по умолчанию DEFAULT_DAYS). Скрипт пробегает
диалоги, оставляет только группы и супергруппы с активностью за окно, читает их
сообщения в окне и считает метрики. «Себя» определяет через get_me().

Вывод — Markdown-таблица в stdout и в data/_overview.md.

Колонки: Чат · Тип · Новых · Активны · Топ-авторы · Упом. меня · Ответы мне · Мои ответы
  - Новых       — сообщений (без сервисных) за последние N дней
  - Активны     — уникальных авторов за период
  - Топ-авторы  — топ-2 по числу сообщений
  - Упом. меня  — сообщения с @упоминанием вас (по username или mention-by-id)
  - Ответы мне  — сообщения-реплаи на ВАШИ сообщения (в пределах окна*)
  - Мои ответы  — ВАШИ сообщения, являющиеся реплаем на чьё-то

* реплаи считаются на ваши сообщения, попавшие в окно N дней (light-приближение).

Запуск:  .venv/bin/python scripts/tg_overview.py            # окно DEFAULT_DAYS
         .venv/bin/python scripts/tg_overview.py --days 14
"""
from __future__ import annotations

import argparse
import asyncio
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Окно обзора по умолчанию (дней). Переопределяется флагом --days.
DEFAULT_DAYS = 7

import yaml
from telethon import TelegramClient, utils
from telethon.tl.types import (
    Channel,
    MessageEntityMention,
    MessageEntityMentionName,
    MessageService,
)

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def chat_type(entity) -> str:
    if isinstance(entity, Channel):
        return "supergroup" if getattr(entity, "megagroup", False) else "channel"
    return "group"


def mentions_me(msg, me) -> bool:
    ent = msg.entities or []
    uname = (me.username or "").lower()
    text = msg.message or ""
    for e in ent:
        if isinstance(e, MessageEntityMentionName) and e.user_id == me.id:
            return True
        if isinstance(e, MessageEntityMention) and uname:
            frag = text[e.offset:e.offset + e.length].lstrip("@").lower()
            if frag == uname:
                return True
    return False


async def analyze_dialog(client, entity, cutoff, me) -> dict | None:
    msgs = []
    async for m in client.iter_messages(entity):
        if m.date is None:
            continue
        if m.date < cutoff:
            break
        if isinstance(m, MessageService):
            continue
        msgs.append(m)

    if not msgs:
        return None

    authors = Counter()
    my_msg_ids = set()
    mention_cnt = 0
    my_reply_cnt = 0
    for m in msgs:
        name = utils.get_display_name(m.sender) if m.sender else f"id{m.sender_id}"
        if m.sender_id is not None:
            authors[name] += 1
        if mentions_me(m, me):
            mention_cnt += 1
        if m.sender_id == me.id:
            my_msg_ids.add(m.id)
            if m.reply_to_msg_id:
                my_reply_cnt += 1

    replies_to_me = sum(
        1 for m in msgs
        if m.reply_to_msg_id in my_msg_ids and m.sender_id != me.id
    )

    top = ", ".join(f"{n} ({c})" for n, c in authors.most_common(2))
    return {
        "new": len(msgs),
        "active": len(authors),
        "top": top,
        "mentions": mention_cnt,
        "replies_to_me": replies_to_me,
        "my_replies": my_reply_cnt,
        "last": max(m.date for m in msgs),
    }


def render_table(rows: list[dict], n: int, generated: datetime) -> str:
    head = (
        f"# Обзор активных чатов за последние {n} дн.\n"
        f"_Сгенерировано: {generated:%Y-%m-%d %H:%M} UTC · "
        f"чатов с активностью: {len(rows)}_\n\n"
        "| Чат | Тип | Новых | Активны | Топ-авторы | Упом. меня | Ответы мне | Мои ответы |\n"
        "|---|---|--:|--:|---|--:|--:|--:|\n"
    )
    body = "".join(
        f"| {r['title']} | {r['type']} | {r['new']} | {r['active']} | {r['top']} "
        f"| {r['mentions'] or ''} | {r['replies_to_me'] or ''} | {r['my_replies'] or ''} |\n"
        for r in rows
    )
    return head + body


async def main() -> int:
    ap = argparse.ArgumentParser(description="Light-обзор активных групп Telegram за N дней")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS,
                    help=f"окно обзора в днях (по умолчанию {DEFAULT_DAYS})")
    args = ap.parse_args()

    load_env(ROOT / ".env")
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        print("ОШИБКА: задайте TG_API_ID и TG_API_HASH в .env")
        return 2

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    session = (ROOT / cfg.get("session", "./secrets/tg")).resolve()
    data_dir = (ROOT / cfg.get("data_dir", "./data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    n = args.days
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=n)

    client = TelegramClient(str(session), int(api_id), api_hash, flood_sleep_threshold=120)
    await client.start(phone=os.environ.get("TG_PHONE"))

    rows = []
    try:
        me = await client.get_me()
        async for dialog in client.iter_dialogs():
            if not dialog.is_group:          # только группы и супергруппы
                continue
            if dialog.date and dialog.date < cutoff:   # дешёвый пре-фильтр по активности
                continue
            stats = await analyze_dialog(client, dialog.entity, cutoff, me)
            if not stats:
                continue
            stats["title"] = (dialog.name or "—").replace("|", "/")
            stats["type"] = chat_type(dialog.entity)
            rows.append(stats)
            print(f"  · {stats['title']}: {stats['new']} новых")
            await asyncio.sleep(0.5)
    finally:
        await client.disconnect()

    rows.sort(key=lambda r: r["new"], reverse=True)
    table = render_table(rows, n, now)
    out = data_dir / "_overview.md"
    out.write_text(table, encoding="utf-8")
    print("\n" + table)
    print(f"Сохранено: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
