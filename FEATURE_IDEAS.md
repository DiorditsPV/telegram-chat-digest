# FEATURE_IDEAS.md — зеркало issue-бэклога (офлайн-индекс)

> **Канонический бэклог — GitHub issues с меткой `feature`** в `DiorditsPV/telegram-chat-digest`.
> Этот файл — зеркало/индекс для офлайн-справки. «Что делать» цикл берёт из issues
> (см. `.claude/feature-loop.md` → «Бэклог: GitHub issues» и `AUTODEV.md`).

**Легенда:** `[ ]` — не реализована, `[x]` — собрана (done-кандидат на ветке). `(#N)` — issue.

## Цельное видение: связная мультимодальная память
Превратить пассивный логгер дельты в **слой памяти, понимающий не только текст, но и медиа**
(изображения, голос, документы, ссылки). Арка из трёх сцепленных слоёв: **захват → обогащение →
использование**. Фундамент — общий модуль шардинга `scripts/shards.py`.

## Роадмап (зеркало issues)
- [x] shards-module (#1, claude/telegram-loop-feature-repo-Pzr6v): общий модуль недельного шардинга
  `scripts/shards.py` (закрыт инвариант #5 — дубли `iso_week_of`). Фундамент для мультимодальности.
- [ ] media-ingest (#8): захват и content-addressed хранение медиа в ingest (`scripts/media_store.py`
  + расширение схемы записи `media_ref`/`media_id`/`media_meta` + download в `tg_sync`). **Слой 1: захват.**
- [ ] media-enrich (#9): обогащение медиа (подпись/OCR/транскрипт/текст документа) — `scripts/tg_enrich.py`
  (append-only `enrichment.jsonl`, очередь) + команда `/tg-enrich` (vision/audio агентом). **Слой 2: обогащение.**
- [ ] multimodal-qa (#10): мультимодальные `context.md` и `/tg-ask` — `scripts/tg_context.py`
  (обогащённое представление с цитатами `#id`+`media_ref`) + апдейт команд. **Слой 3: использование.**

## Закрыто как superseded (пивот на мультимодальность)
#2 tg-stats, #3 tg-search, #4 tg-export, #5 tg-doctor, #6 config-validate, #7 tg-threads —
точечные CLI-утилиты, поглощены роадмапом #8–#10 или вынесены из скоупа. При необходимости — переоткрыть.
