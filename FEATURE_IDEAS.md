# FEATURE_IDEAS.md — зеркало issue-бэклога (офлайн-индекс)

> **Канонический бэклог — GitHub issues с меткой `feature`** в `DiorditsPV/telegram-chat-digest`.
> Этот файл — зеркало/индекс для офлайн-справки. «Что делать» цикл берёт из issues
> (см. `.claude/feature-loop.md` → «Бэклог: GitHub issues» и `AUTODEV.md`).

**Легенда:** `[ ]` — не реализована, `[x]` — собрана (done-кандидат на ветке). `(#N)` — issue.

## Цельное видение: «Решения и темы — причина → следствие»
Легковесно и без поддержки **понимать суть рабочих задач** и **причину → следствие принятых решений
по темам**. Простые решения, много пользы. В духе проекта: плоский JSONL + рассуждает сессия Claude
(без отдельного LLM-ключа), низкая поддержка. Фундамент — `scripts/shards.py`.

## Роадмап (зеркало issues)
- [x] shards-module (#1, claude/telegram-loop-feature-repo-Pzr6v): общий модуль недельного шардинга
  `scripts/shards.py` (закрыт инвариант #5). Фундамент.
- [x] decision-log (#11, claude/telegram-loop-feature-repo-Pzr6v): лёгкий журнал решений/задач по темам —
  `data/<name>/decisions.jsonl` (append-only event-log) + `scripts/decisions.py` (свёртка/доска по темам)
  + `/tg-sync` дозаписывает + команда `/tg-topics`. **Слой данных.**
- [x] tg-why (#12, claude/telegram-loop-feature-repo-Pzr6v): запрос «причина → следствие» по теме/решению —
  `history`/`search`/`render_trace` в `decisions.py` + команда `/tg-why <тема>`. **Слой использования.**

## Закрыто как superseded / not planned
- #2 tg-stats, #3 tg-search, #4 tg-export, #5 tg-doctor, #6 config-validate, #7 tg-threads —
  точечные CLI-утилиты, не дотягивают до уровня фичи.
- #8 media-ingest, #9 media-enrich, #10 multimodal-qa — мультимодальность вне цели проекта.
