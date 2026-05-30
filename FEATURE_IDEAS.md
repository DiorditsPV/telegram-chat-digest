# FEATURE_IDEAS.md — зеркало issue-бэклога (офлайн-индекс)

> **Канонический бэклог — GitHub issues с меткой `feature`** в `DiorditsPV/telegram-chat-digest`.
> Этот файл — лишь зеркало/индекс для офлайн-справки. «Что делать» цикл берёт из issues
> (см. `.claude/feature-loop.md` → «Бэклог: GitHub issues» и `AUTODEV.md`).

**Легенда:** `[ ]` — не реализована, `[x]` — собрана (done-кандидат на ветке). `(#N)` — issue.
Спеки фич — в `.claude/features/<slug>.md` (frontmatter `issue: N`); каталог — `FEATURES.md`.

Все фичи — аналитика/утилиты **над уже выгруженными недельными шардами** (`data/<name>/*.jsonl`):
чистые модули (stdlib + `yaml` + `shards`), без `telethon`, тестируемые без сети и Telegram.

## Бэклог (зеркало issues)
- [x] shards-module (#1, claude/telegram-loop-feature-repo-Pzr6v): общий модуль недельного шардинга
  `scripts/shards.py` (закрыт инвариант #5 — дубли `iso_week_of` в 3 скриптах).
- [ ] tg-stats (#2): `scripts/tg_stats.py` — статистика по шардам (сообщений/неделю, топ-авторы,
  средняя длина, активные дни, доля медиа), CLI `--name/--weeks`.
- [ ] tg-search (#3): `scripts/tg_search.py` — поиск по сырым шардам (подстрока/regex + фильтры
  author/week/date-range), `#id`+сниппет; команда `.claude/commands/tg-search.md`.
- [ ] tg-export (#4): `scripts/tg_export.py` — экспорт сообщений за период в Markdown или CSV.
- [ ] tg-doctor (#5): `scripts/tg_doctor.py` — проверка целостности шардов (запись в правильном
  шарде, монотонность/дубли id, согласованность state.json).
- [ ] config-validate (#6): `scripts/validate_config.py` — валидация `config.yaml` (дубли name,
  обязательные поля, тип topic/chat).
- [ ] tg-threads (#7): `scripts/tg_threads.py` — реконструкция цепочек ответов по `reply_to`,
  текстовый рендер дерева тредов.
