---
description: Причина → решение → следствие по теме/решению (из журнала решений, с цитатами #id)
---

Ты отвечаешь на вопрос «почему приняли X и что из этого вышло» по конкретной теме
или решению, опираясь на журнал решений `data/<name>/decisions.jsonl` (его ведёт
`/tg-sync`) и подтверждая дословными цитатами из недельных шардов.

Запрос пользователя (тема/решение/вопрос): `$ARGUMENTS`

## 1. Выбор цели
Если пользователь назвал чат — работай по нему. Иначе ищи во всех целях из
`config.yaml`, где есть `data/<name>/decisions.jsonl`.

## 2. Найти сущность и показать цепочку причина→следствие
Из корня проекта:

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
import decisions
name = "<name>"
query = """$ARGUMENTS"""
events = decisions.load(f"data/{name}/decisions.jsonl")
items = decisions.items_list(decisions.fold(events))
matches = decisions.search(items, query)
if not matches:
    print("NO_MATCH")
else:
    for it in matches:
        print(decisions.render_trace(events, it["item_id"]))
        print("REFS", it.get("refs"))
PY
```

(Системного python3 достаточно — `decisions.py` чистый, telethon не нужен.)

## 3. Подтвердить цитатами
Для `refs` (#id) найденных сущностей подтяни дословные сообщения из недельных шардов
(`data/<name>/*.jsonl`) грепом по `"id": <n>` и процитируй ключевые строки с автором/датой.

## 4. Если совпадений нет (`NO_MATCH`)
Журнал не покрывает тему — деградируй к поведению `/tg-ask`: ответь по `context.md`
и грепу шардов, и предложи, что после следующего `/tg-sync` тема попадёт в журнал.

## 5. Ответ
Связно изложи: **причина** (что привело к решению) → **решение/действие** → **следствие**
(что вышло, текущий статус), с цитатами `#id`. Без воды; не выдумывай — только то, что есть в данных.
