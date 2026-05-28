#!/usr/bin/env python3
"""Discover: выгрузить N последних диалогов Telegram в файл-кандидат конфига.

Берёт N самых свежих диалогов (любого типа: группы, супергруппы, каналы, личка)
и пишет их как ЗАКОММЕНТИРОВАННЫЕ цели в отдельный файл (по умолчанию
config.discovered.yaml). Владелец просматривает файл, раскомментирует нужные
(убрать "# " в начале строк) и переносит в config.yaml для /tg-sync.

Файл-результат содержит реальные имена/юзернеймы/id чатов — он в .gitignore и
НЕ должен попадать в публичную историю.

Запуск:  .venv/bin/python scripts/tg_discover.py               # 20 последних
         .venv/bin/python scripts/tg_discover.py --last 50
         .venv/bin/python scripts/tg_discover.py --out my_candidates.yaml
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
from pathlib import Path

import yaml
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_LAST = 20
DEFAULT_OUT = "config.discovered.yaml"

# Компактная транслитерация RU -> latin для читаемых slug'ов.
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def slugify(title: str, fallback_id: int | None) -> str:
    """Имя -> slug для data/<name>/. Транслитерует RU; пустое -> chat-<id>."""
    s = "".join(_TRANSLIT.get(ch, ch) for ch in (title or "").lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or (f"chat-{fallback_id}" if fallback_id is not None else "chat")


def entity_type(entity) -> str:
    if isinstance(entity, Channel):
        return "supergroup" if getattr(entity, "megagroup", False) else "channel"
    if isinstance(entity, User):
        return "bot" if getattr(entity, "bot", False) else "user"
    if isinstance(entity, Chat):
        return "group"
    return type(entity).__name__


def chat_ref(entity) -> str:
    """Ссылка на чат для поля config.chat: @username или числовой id."""
    uname = getattr(entity, "username", None)
    if uname:
        return f'"@{uname}"'
    return str(getattr(entity, "id", ""))


def render(rows: list[dict], last: int) -> str:
    """Текст файла-кандидата: targets: с закомментированными целями."""
    head = (
        f"# Сгенерировано scripts/tg_discover.py — {len(rows)} последних диалогов "
        f"(--last {last}).\n"
        "# Все цели ЗАКОММЕНТИРОВАНЫ. Раскомментируйте нужные (убрать \"# \" в начале\n"
        "# строк) и перенесите в config.yaml. Поле chat: @username / числовой id /\n"
        "# точное название. topic: id топика (для форумов) или null.\n"
        "#\n"
        "# ВНИМАНИЕ: тут реальные имена/id чатов — файл в .gitignore, не коммитьте.\n\n"
        "targets:\n"
    )
    blocks = []
    for r in rows:
        blocks.append(
            f"#   # [{r['type']}] {r['title']} · id {r['id']}\n"
            f"#   - name: {r['slug']}\n"
            f"#     chat: {r['ref']}\n"
            f"#     topic: null\n"
        )
    return head + "#\n".join(blocks)


async def main() -> int:
    ap = argparse.ArgumentParser(description="Выгрузить N последних диалогов в файл-кандидат конфига")
    ap.add_argument("--last", type=int, default=DEFAULT_LAST,
                    help=f"сколько последних диалогов взять (по умолчанию {DEFAULT_LAST})")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help=f"куда писать (по умолчанию {DEFAULT_OUT} в корне проекта)")
    args = ap.parse_args()

    load_env(ROOT / ".env")
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        print("ОШИБКА: задайте TG_API_ID и TG_API_HASH в .env (см .env.example)")
        return 2

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    session = (ROOT / cfg.get("session", "./secrets/tg")).resolve()

    client = TelegramClient(str(session), int(api_id), api_hash, flood_sleep_threshold=120)
    await client.start(phone=os.environ.get("TG_PHONE"))

    rows = []
    try:
        async for dialog in client.iter_dialogs(limit=args.last):
            ent = dialog.entity
            rows.append({
                "title": (dialog.name or "—").replace("\n", " ").strip(),
                "id": getattr(ent, "id", ""),
                "type": entity_type(ent),
                "slug": slugify(dialog.name, getattr(ent, "id", None)),
                "ref": chat_ref(ent),
            })
    finally:
        await client.disconnect()

    out_path = (ROOT / args.out).resolve()
    out_path.write_text(render(rows, args.last), encoding="utf-8")
    print(f"Записано {len(rows)} диалогов-кандидатов в {out_path}")
    print("Раскомментируйте нужные цели и перенесите в config.yaml для /tg-sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
