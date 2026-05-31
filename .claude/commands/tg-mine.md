---
description: Решения и задачи на заданном человеке («что на мне / на нём») из журнала решений
---

Ты показываешь активные решения и задачи, закреплённые за человеком (ответственный
`owner` в журнале `data/<name>/decisions.jsonl`). Цель — быстро понять «что на мне»
или «что висит на ком-то».

Кто (имя/@handle): `$ARGUMENTS` — если пусто, возьми поле `me:` из `config.yaml`
(если и его нет — попроси уточнить, кого показать).

## 1. Выбор цели
Если пользователь назвал чат — по нему. Иначе по всем целям из `config.yaml`,
где есть `data/<name>/decisions.jsonl`.

## 2. Срез по ответственному
Из корня проекта (системного python3 достаточно):

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
import decisions
name = "<name>"
who = """$ARGUMENTS""".strip() or "<me из config.yaml>"
items = decisions.items_list(decisions.fold(decisions.load(f"data/{name}/decisions.jsonl")))
mine = decisions.for_owner(items, who)
active = decisions.filter_status(mine, "open", "decided")
print(decisions.render_board(active, title=f"На {who} — {name}"))
PY
```

(По умолчанию показываем активное — `open`/`decided`. Если просили всё, включая
закрытое — убери `filter_status`.)

## 3. Ответ
Покажи список с темами, статусами и `#id`. Подсвети, что требует действия. При
вопросе «почему/что вышло» по конкретному пункту предложи `/tg-why <тема>`.
