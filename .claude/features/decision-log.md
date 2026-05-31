---
slug: decision-log
title: Лёгкий журнал решений/задач по темам (причина→следствие)
status: done
created: 2026-05-30
issue: 11
branch: claude/telegram-loop-feature-repo-Pzr6v
verify: pass
review: ok
---

## Проблема / цель
`context.md` — свободная проза; нет быстрого структурированного среза «по теме: что решили, **почему**
(причина), **что из этого вышло** (следствие), статус». Цель — лёгкий слой данных, дающий понимание
сути рабочих задач и причинно-следственных связей решений, без отдельного LLM-ключа и тяжёлой поддержки.

## Поведение / UX
- На каждом `/tg-sync` агент (тем же проходом, что ведёт `context.md`) дозаписывает в
  `data/<name>/decisions.jsonl` события решений/задач: тема, формулировка, **why** (причина из
  обсуждения), **effect** (следствие/итог), статус, `refs` (#id). Append-only — история не переписывается.
- `/tg-topics` рендерит «доску»: по темам — текущие задачи/решения и статусы (суть задач с одного взгляда).
- Скрипт чистый, офлайн; «интеллект» (выделение решений) — у сессии Claude, как и для `context.md`.

## Затрагиваемые слои и файлы
- Данные/логика (`scripts/`): новый `decisions.py` (чистый, переиспользует `shards` для JSONL).
- Агентский слой (`.claude/commands/`): расширить `tg-sync.md` (шаг ведения журнала); новый `tg-topics.md`.
- Пример: `examples/team-platform/decisions.jsonl` + сгенерированная `examples/team-platform/topics.md`.
- tests: `tests/test_decisions.py`.
- Документация: README/AGENTS — артефакт `decisions.jsonl`, команды, инвариант append-only.

## Модель данных
`data/<name>/decisions.jsonl` — **append-only event-log** (в `.gitignore`, как вся `data/`). Событие:
```json
{"ts": 1772530000, "item_id": "release-v2.3", "topic": "Релиз v2.3", "kind": "decision",
 "statement": "...", "why": "...", "effect": "...", "status": "decided", "refs": [105], "note": "", "by": "tg-sync"}
```
- `item_id` — стабильный slug сущности (решение/задача); события с одним `item_id` сворачиваются.
- `kind` ∈ {`decision`,`task`}; `status` ∈ {`open`,`decided`,`done`,`reversed`}.
- Свёртка `fold`: по `item_id` поля=последние непустые, `refs`=объединение, `status`=последний,
  трекаются `ts_first`/`ts_last`. Причина→следствие во времени = последовательность событий (см. #12).

## Решения (с обоснованием)
- **Event-log (append-only), а не перезапись** — ложится на главный инвариант проекта (`*.jsonl`
  append-only) и сохраняет историю изменений статуса (нужна для причина→следствие).
- **Плоский JSONL + агент рассуждает** — в духе проекта (без БД, без LLM-ключа); поддержка низкая.
- **`item_id`-slug присваивает агент** — стабильная привязка событий к одной сущности; альтернатива
  (генерить id) ломает идемпотентность дозаписи.
- **Переиспользуем `shards.read_jsonl`** — единый путь чтения JSONL, без дублирования.

## План реализации (чеклист для feature-build)
1. [ ] `scripts/decisions.py`: `validate_event`, `load`, `fold`, `items_list`, `by_topic`,
   `filter_status`, `append_event`, `render_board`
2. [ ] `examples/team-platform/decisions.jsonl` (по сообщениям #102/#105/#106/#107) + `topics.md`
3. [ ] `.claude/commands/tg-sync.md`: шаг «вести журнал решений»; `.claude/commands/tg-topics.md` (новый)
4. [ ] `tests/test_decisions.py`: fold/merge, by_topic, filter_status, validate, render_board
5. [ ] README/AGENTS: артефакт `decisions.jsonl`, команды `/tg-topics`, инвариант
6. [ ] Verify: ruff/format/mypy по `decisions.py`+tests + pytest

## Тесты / приёмка
- [ ] `pytest` зелёный; `fold` сворачивает несколько событий одного `item_id` (последний статус,
  объединение refs); `by_topic`/`filter_status` корректны; `render_board` содержит темы и статусы.
- [ ] `validate_event` ловит плохой `kind`/`status`/отсутствие `item_id`.
- [ ] `python3 -c "import decisions; print(decisions.render_board(...))"` на примере читается.
- [ ] `data/` (включая `decisions.jsonl`) — вне git.

## Риски / открытые вопросы
- Качество журнала зависит от агента в `/tg-sync` — но это та же модель доверия, что и для `context.md`.
- `item_id`-коллизии между темами: договорённость — slug уникален глобально по чату (префикс темой при риске).
