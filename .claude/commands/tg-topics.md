---
description: Показать доску решений и задач по темам (суть рабочих задач с одного взгляда)
---

Ты показываешь «доску» — текущие задачи и решения по темам из журнала решений
`data/<name>/decisions.jsonl` (его ведёт `/tg-sync`). Цель: быстро понять суть
рабочих задач и статусы, без перечитывания чатов.

## 1. Выбор цели
Если пользователь назвал чат — работай по нему (`data/<name>/`). Иначе пройди по
всем целям из `config.yaml`, у которых есть `data/<name>/decisions.jsonl`.

## 2. Рендер доски
Для каждой цели запусти из корня проекта:

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
import decisions
name = "<name>"            # подставь имя цели
path = f"data/{name}/decisions.jsonl"
items = decisions.items_list(decisions.fold(decisions.load(path)))
print(decisions.render_board(items, title=f"Доска решений и задач — {name}"))
PY
```

(Системного python3 достаточно — `decisions.py` чистый, telethon не нужен.)

## 3. Фильтры (по запросу пользователя)
- «что открыто» / активные задачи → `decisions.filter_status(items, "open", "decided")`
  перед `render_board`.
- «по теме X» → отфильтруй `items` по `it["topic"]`.

## 4. Ответ
Покажи доску. Если просили срез (только открытое / по теме) — применяй фильтр.
По каждой строке доступны `#id` — при просьбе «почему/что вышло» по теме предложи
команду `/tg-why <тема>` (цепочка причина→следствие).
