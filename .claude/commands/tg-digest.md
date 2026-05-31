---
description: Обзор движения решений/задач за период + что зависло (по журналу решений)
---

Ты показываешь дайджест по рабочим задачам: что нового/обновилось/завершилось за
период и что **зависло** (open/decided без движения), по журналу решений
`data/<name>/decisions.jsonl` (его ведёт `/tg-sync`).

Окно (дней): `$ARGUMENTS` — если пусто, бери 7.

## 1. Выбор цели
Если пользователь назвал чат — по нему. Иначе по всем целям из `config.yaml`,
где есть `data/<name>/decisions.jsonl`.

## 2. Посчитать и отрендерить дайджест
Из корня проекта (системного python3 достаточно — `tg_digest.py` чистый):

```bash
python3 - <<'PY'
import sys, time; sys.path.insert(0, "scripts")
import decisions, tg_digest
name = "<name>"
days = int("""$ARGUMENTS""".strip() or 7)
now = int(time.time())
events = decisions.load(f"data/{name}/decisions.jsonl")
result = tg_digest.digest(events, since_ts=now - days * 86400, now_ts=now)
print(tg_digest.render_digest(result, title=f"Дайджест — {name} ({days} дн.)"))
PY
```

## 3. Ответ
Покажи дайджест. Кратко резюми важное: ключевые завершённые решения, новые задачи
и — главное — **зависшее** (что требует внимания). По строкам доступны `#id`; при
просьбе «почему так вышло по теме X» предложи `/tg-why <тема>`.
