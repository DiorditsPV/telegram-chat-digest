# FEATURE_IDEAS.md — бэклог фич для генерации

Источник идей для пайплайна **feature-design → feature-build**. Контекст «что уже сделано» —
в `FEATURES.md`; спроектированные спеки — в `.claude/features/<slug>.md`.

**Легенда:** `[ ]` — не реализована, `[x]` — реализована (в скобках ветка).
**Правила:** одна идея = один `slug` (kebab-case). Дедуп по slug. Не дублируй то, что уже в `FEATURES.md`.
Формат строки: `- [ ] <slug>: <краткое описание> — <подсказка по слоям/объёму>`.

Все идеи ниже — фичи аналитики/утилит **над уже выгруженными недельными шардами**
(`data/<name>/*.jsonl`): чистые модули (stdlib + `yaml` + `shards`), без `telethon`, полностью
тестируемые на фикстурах/`examples/` без сети и Telegram-сессии.

## Идеи
<!-- Добавляй идеи сюда. feature-build переносит реализованные: - [ ] <slug> … → - [x] <slug> (<branch>) -->
- [x] shards-module (claude/telegram-loop-feature-repo-Pzr6v): вынести дублируемую логику недельного
  шардинга (`iso_week_of`, чтение/запись/бакетизация JSONL) в общий `scripts/shards.py` + юнит-тесты;
  перевести `tg_sync.py`, `import_export.py`, `migrate_to_weekly.py` на него — закрыть инвариант #5.
- [ ] tg-stats: `scripts/tg_stats.py` — статистика по шардам цели (сообщений/неделю, топ-авторы,
  средняя длина, активные дни, доля медиа) с CLI `--name/--weeks`; ядро-агрегатор + тесты — scripts/ + tests/.
- [ ] tg-search: `scripts/tg_search.py` — поиск по сырым шардам (подстрока/regex + фильтры author/
  week/date-range), вывод `#id` + сниппет; плюс агентская команда `.claude/commands/tg-search.md` — scripts/ + .claude/commands/ + tests/.
- [ ] tg-export: `scripts/tg_export.py` — экспорт сообщений цели за период в читаемый Markdown или CSV
  (`--format md|csv`, `--weeks`); ядро-рендер + тесты — scripts/ + tests/.
- [ ] tg-doctor: `scripts/tg_doctor.py` — проверка целостности шардов (каждая запись в правильном
  ISO-week-шарде, монотонность id, дубли id, согласованность с state.json); отчёт + exit-code — scripts/ + tests/.
- [ ] config-validate: `scripts/validate_config.py` — валидация `config.yaml` (дубли name/целей,
  обязательные поля, тип topic, корректность chat) с понятными ошибками; ядро + тесты — scripts/ + tests/.
- [ ] tg-threads: `scripts/tg_threads.py` — реконструкция цепочек ответов по `reply_to` в рамках
  шарда/периода (дерево тредов, корни без ответов), текстовый рендер дерева; ядро + тесты — scripts/ + tests/.
- [ ] tg-mentions: `scripts/tg_mentions.py` — выбрать сообщения, упоминающие заданного пользователя
  (@username/имя) или адресованные ему (reply на его сообщения) — scripts/ + tests/. (на потом)
- [ ] tg-digest-range: собрать «дайджест-заготовку» (markdown) по периоду из шардов для ручной
  суммаризации без обращения к context.md — scripts/ + tests/. (на потом)
