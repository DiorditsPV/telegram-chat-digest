---
slug: shards-module
title: Общий модуль недельного шардинга (shards.py)
status: done
created: 2026-05-30
branch: claude/telegram-loop-feature-repo-Pzr6v
verify: pass
review: ok
---

## Проблема / цель
Логику ISO-недельного шардинга (`iso_week_of` + бакетизация записей по неделям + дозапись в шарды)
дублируют **три** скрипта: `tg_sync.py`, `import_export.py`, `migrate_to_weekly.py` (инвариант #5 в
`AGENTS.md`/README: «менять согласованно»). Любая правочка логики недели рискует разъехаться между
ними. Цель — единый источник истины `scripts/shards.py` (чистый stdlib, без telethon), покрытый
тестами, на который переходят все три скрипта. Бонус: переиспользуемый API для будущих фич аналитики.

## Поведение / UX
Поведение скриптов не меняется (рефактор без смены наблюдаемого результата): те же имена шардов
`YYYY-Www` (UTC), `undated` для `ts=None`, тот же append-only формат строки JSONL. Снаружи (CLI,
файлы данных) — ничего не меняется.

## Затрагиваемые слои и файлы
- ETL (`scripts/`): новый `shards.py`; правки `tg_sync.py`, `import_export.py`, `migrate_to_weekly.py`
  (убрать локальные `iso_week_of` и inline-бакетизацию, импортировать `shards`).
- tests: `tests/test_shards.py` — iso_week_of (граница недели/год, undated), bucket_by_week,
  append_by_week (дозапись/стык недель), read_jsonl/read_records.

## Модель данных
Без изменений схемы. Формализуем имя шарда и операции над ним. `ts=None → "undated"` сохраняется.

## Решения (с обоснованием)
- **Плоский модуль `shards.py`, импорт `import shards`** — скрипты запускаются как `python3 scripts/x.py`,
  их каталог в `sys.path[0]`, поэтому сиблинг-импорт работает; тесты — через `pythonpath=scripts`,
  mypy — через `mypy_path=scripts`. Альтернатива (пакет `scripts/`) ломает текущий запуск «на месте».
- **`append_by_week(out_dir, records, mode="a")`** покрывает оба паттерна: `tg_sync`/`migrate` (append),
  `import_export` (пишет в гарантированно пустой каталог — append эквивалентен write). Параметр `mode`
  оставлен на случай явного «w».
- **`bucket_by_week` отдельно** — нужен `migrate_to_weekly` для печати плана (dry-run) до записи.
- Без telethon/yaml в модуле — чтобы тесты и фичи аналитики импортировали его без установки Telethon.

## План реализации (чеклист для feature-build)
1. [ ] `scripts/shards.py`: `iso_week_of`, `bucket_by_week`, `append_by_week`, `iter_jsonl`,
   `read_jsonl`, `shard_paths`, `read_records` — коммит в составе фичи
2. [ ] Рефактор `tg_sync.py` → `import shards`, `append_by_week` через модуль, убрать локальный дубль
3. [ ] Рефактор `import_export.py` → `shards.append_by_week`, убрать локальный `iso_week_of`/inline-цикл
4. [ ] Рефактор `migrate_to_weekly.py` → `shards.bucket_by_week` (план) + `shards.append_by_week` (запись)
5. [ ] `tests/test_shards.py` + обновить `AGENTS.md`/README инвариант #5 (единый источник)
6. [ ] Verify: ruff/format/mypy по затронутым .py + pytest

## Тесты / приёмка
- [ ] `pytest -q` зелёный; `test_shards` покрывает границу недели, undated, дозапись, чтение.
- [ ] `ruff check`/`ruff format --check`/`mypy` по `scripts/shards.py` + 3 рефакторенных скрипта + tests.
- [ ] `python3 scripts/migrate_to_weekly.py --dry-run` и `--help` работают (без data — «нечего мигрировать»).

## Риски / открытые вопросы
- Рефактор затрагивает `tg_sync.py`, который импортирует telethon → его не импортируем в тестах;
  проверяем только статикой (ruff/mypy). Поведенческое покрытие — через `shards.py` напрямую.
