# feature-loop — конфиг фреймворка для telegram-chat-digest

Единственная точка кастомизации фреймворка. Скиллы **feature-design** и **feature-build**
читают этот файл первым делом (`cat .claude/feature-loop.md`), чтобы узнать карту проекта,
конвенции и как проверять изменения. Всё остальное в фреймворке — проектно-независимо.

Проект: light-пайплайн выгрузки дельты чатов Telegram (Telethon) + ведение живого контекста и
Q&A силами сессии Claude Code. Подробная карта — в `README.md` (раздел «Карта проекта») и `AGENTS.md`.

---

## Настройки

| ключ | значение | смысл |
|---|---|---|
| `branch_prefix` | `feature/` | ветки фич называются `<branch_prefix><slug>` |
| `default_branch` | `main` | куда писать ledger |
| `backlog_source` | **GitHub issues** | источник истины «что делать» — open issues с меткой `feature` (см. ниже) |
| `issue_repo` | `DiorditsPV/telegram-chat-digest` | репозиторий issues (через GitHub MCP-инструменты) |
| `issue_label` | `feature` | метка фич-бэклога |
| `ideas_file` | `FEATURE_IDEAS.md` | **зеркало** issue-бэклога (офлайн-индекс); канон — issues |
| `features_catalog` | `FEATURES.md` | каталог реализованных фич (генерится `catalog.py`) |
| `specs_dir` | `.claude/features` | спеки фич `<slug>.md` (frontmatter содержит `issue: <N>`) |
| `commit_trailer` | `—` | трейлер коммита не требуется |

**Переиспользуемые скиллы** (доменные слэш-команды проекта — агентский слой). `feature-build`
вызывает их вместо дублирования логики, когда фича затрагивает соответствующий поток:

```
reused_skills:
  - tg-sync: выгрузка дельты и обновление context.md/delta-log.md
  - tg-ask: ответ по истории (context.md + греп по шардам)
  - tg-overview: обзор активных групп за N дней
  - tg-discover: список последних диалогов в кандидаты целей
```

> Эти команды требуют живого Telegram-аккаунта/сессии и недоступны в CI/песочнице. Для
> фич аналитики/утилит над уже выгруженными шардами они НЕ нужны — работай с `data/<name>/*.jsonl`
> напрямую (формат — в `examples/team-platform/`).

---

## Бэклог: GitHub issues (источник истины «что делать»)

Канонический бэклог — **открытые GitHub issues с меткой `feature`** в `DiorditsPV/telegram-chat-digest`
(не markdown-файл). `FEATURE_IDEAS.md` — лишь офлайн-зеркало/индекс для справки. Цикл работает так:

1. **Выбор фичи** (feature-design): взять следующий открытый issue с меткой `feature`, у которого ещё
   нет спеки/ветки (нет связанной `.claude/features/<slug>.md` со `status: building|done`). Через GitHub
   MCP: `list_issues(owner, repo, state=OPEN, labels=["feature"])`. Бэклог пуст → можно завести новый
   issue из пробела (`issue_write method=create`, метка `feature`), затем проектировать его.
2. **Спека ↔ issue**: `slug` фичи = из заголовка issue `feat(<slug>): …`. В frontmatter спеки —
   обязательное поле **`issue: <N>`** (номер issue). Так каталог и issue всегда связаны.
3. **Привязка кода**: коммит фичи заканчивается ссылкой на issue — `feat(<slug>): <title> (#<N>)`.
4. **Статус обратно в issue** (feature-build, по завершении): постит коммент в issue #N через
   `add_issue_comment` — что фича собрана (done-кандидат): ветка/коммит, результат Verify + code-review,
   путь спеки. **Issue НЕ закрывается на build** (done ≠ shipped): закрытие — при ручной выкатке
   (feature-ship, мёрж в `main`) со `state_reason: completed`. Красный Verify → коммент о проблеме,
   issue остаётся открытым.
5. **Идемпотентность по issue**: прежде чем брать issue, проверь, нет ли уже спеки с этим `issue:` в
   `status: building|done` — если есть, пропусти (не дублируй).

> Эти шаги используют GitHub MCP-инструменты (`mcp__github__list_issues`, `issue_write`,
> `add_issue_comment`, `issue_read`). Сетевые операции — только по issue-бэклогу; код по-прежнему
> коммитится локально (push/PR/мёрж — решение человека).

---

## Карта проекта (где что лежит)

- **Выгрузка/ETL** (`scripts/`):
  - `tg_sync.py` — инкрементальная выгрузка дельты по `min_id` через Telethon; нарезка по
    недельным шардам; запись `state.json` и `.last_delta.json`. Импортирует `telethon` на верхнем
    уровне — **в тестах/песочнице не импортируется** (telethon не установлен).
  - `tg_overview.py` — обзор активных групп за N дней (`--days`); самостоятелен.
  - `tg_discover.py` — N последних диалогов → `config.discovered.yaml` (кандидаты в цели).
  - `import_export.py` — разовый сидинг из экспорта Telegram Desktop (`result.json`) → шарды.
  - `migrate_to_weekly.py` — разовая миграция старого `raw.jsonl` → недельные шарды.
  - `shards.py` — **общий модуль** недельного шардинга (ISO-неделя, чтение/запись/бакетизация
    JSONL). Чистый stdlib, без telethon — переиспользуй его в новых фичах аналитики.
- **Агентский слой** (`.claude/commands/*.md`): `/tg-sync`, `/tg-ask`, `/tg-overview`, `/tg-discover`.
- **Конфиг** (`config.yaml`): список целей (чат, топик) + параметры выгрузки. Загрузка — `yaml.safe_load`.
- **Данные** (`data/<name>/`, в `.gitignore`): недельные шарды `<YYYY-Www>.jsonl` (источник истины,
  append-only), `delta-log.md`, `context.md`, `.last_delta.json`; `data/state.json` — `last_id` на цель.
- **Пример формата артефактов**: `examples/team-platform/` (синтетика; единственное, что в git из data-слоя).
- **Тесты/прогон**: `tests/` (pytest). Скрипты-аналитики чистые (stdlib+yaml+shards) и импортируются
  в тестах напрямую (`pythonpath=scripts`). Запуск скрипта руками: `.venv/bin/python scripts/<...>.py`.

### Схема записи JSONL (одно сообщение)
```json
{"id": 102, "date": "2026-03-02T09:31:00", "ts": 1772443860, "from": "Bob Dev",
 "from_id": 111000002, "topic": 12, "reply_to": 101, "edited": null, "fwd": null,
 "media": null, "text": "..."}
```
Поля: `id` (int, монотонный), `ts` (epoch UTC, может быть `None` → шард `undated`), `from`/`from_id`,
`topic`, `reply_to` (id сообщения, на которое ответ), `edited`/`fwd`/`media` (nullable), `text`.

---

## Конвенции и грабли (ВАЖНО)

- **Источник истины по коду** смотри через `cat`/`grep` (не кэширующий Read); формат данных — из
  `examples/team-platform/`.
- **Никогда не коммить реальные данные/секреты:** `.env`, `secrets/`, `*.session`, вся `data/` — в
  `.gitignore`. В git идёт только синтетический `examples/` и тесты на нём/на фикстурах.
- **`*.jsonl` — append-only источник истины.** Не редактируй и не удаляй записанное; не возвращай единый
  `raw.jsonl`. Нарезка — по ISO-неделе даты сообщения (UTC), имя шарда `YYYY-Www` (`undated` для `ts=None`).
- **Тянем только новые сообщения** (дельта по `min_id`); правки/удаления/реакции после выгрузки не догоняем.
- **`context.md` мерджится, не переписывается.**
- **ISO-неделя — единый источник `shards.iso_week_of`.** Раньше логику дублировали `tg_sync.py`,
  `import_export.py`, `migrate_to_weekly.py` — теперь все импортируют `shards`. Не возрождай дубли.
- **Новый скрипт-аналитика** = чистый модуль (stdlib + `yaml` + `shards`), без `telethon` на верхнем
  уровне, с функцией-ядром (тестируемой) и тонким `main()`/CLI. Пути ищи относительно `Path(__file__)`.
- **Кодстайл**: соблюдай ruff (`ruff format`) — отступы/строки 4 пробела, длинные строки переносим.

---

## Verify (как доказать, что ничего не сломалось) — ОБЯЗАТЕЛЬНО

Гейт скоупится на **затронутые фичей файлы** (легаси-скрипты исторически не проходят линт/типы целиком —
не лечим их «заодно», только то, что реально правим), плюс полный прогон тестов.

```bash
# Линт и формат — по затронутым .py (скрипты + тесты этой фичи):
ruff check scripts/<touched>.py tests/
ruff format --check scripts/<touched>.py tests/
# Типы — по затронутым модулям (telethon/yaml игнорятся через ignore_missing_imports в pyproject):
mypy scripts/<touched>.py
# Тесты — весь набор (быстрый, на фикстурах, без сети/Telegram):
pytest -q
```

- **Когда что нужно:** правка/добавление `.py` → `ruff check` + `ruff format --check` + `mypy` по этим
  файлам; любая логика → покрой `pytest` (тест на фикстурах в `tests/`, без сети). Правка только доков/спек
  → тесты гонять не нужно. Правишь модуль, на который опираются тесты — обнови тесты.
- **Зелёный =** все четыре команды exit 0 (ruff без ошибок, format без «would reformat», mypy без error,
  pytest все прошли).
- Dev-инструменты: `pip install -r requirements-dev.txt` (ruff, mypy, pytest, types-PyYAML). Конфиг
  ruff/mypy/pytest — в `pyproject.toml`.
- **Не импортируй `telethon` в тестах** (не установлен в песочнице) — тестируй чистые модули
  (`shards`, аналитика) напрямую; для `tg_sync.py` ограничься `ruff`/`mypy`.

---

## Deploy (как фича попадает в прод)

- `trigger`: `none`
  - Это локальный инструмент/CLI без сервиса: «деплой» = пользователь обновляет свой клон и гоняет
    скрипты/слэш-команды у себя. Скилл **feature-ship** при ручной выкатке просто мёржит ветку фичи в
    `main` и метит спеку `shipped` (CI/команд деплоя нет).
- `commands`: —
- `checks`: после мёржа `pytest -q` на `main` зелёный; новые скрипты запускаются `python3 scripts/<...>.py --help`.
