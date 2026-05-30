# feature-loop — ПРИМЕР заполненного конфига (сервис интервью «граф вопросов»)

Образец того, как выглядит `.claude/feature-loop.md`, заполненный под реальный проект.
Скопируй структуру в свой `feature-loop.md` и замени содержимое.

---

## Настройки

| ключ | значение |
|---|---|
| `branch_prefix` | `feature/` |
| `default_branch` | `main` |
| `ideas_file` | `FEATURE_IDEAS.md` |
| `features_catalog` | `FEATURES.md` |
| `specs_dir` | `.claude/features` |
| `commit_trailer` | `Co-Authored-By: …` (требует окружение) |

**Переиспользуемые скиллы:**
```
reused_skills:
  - interview-ideas:    контент/вопросы — создать, развернуть, реализовать идеи в ноды
  - interview-refactor: правка сложности/тегов/подачи существующих вопросов
  - interview-balance:  оценка покрытия и пробелов (если фича про наполнение)
  - interview-verify:   любая проверка по ходу и в конце (обёртка над секцией Verify)
```

---

## Карта проекта (где что лежит)

- **Backend** (`backend/app/`): `models.py` (pydantic `Node`, `extra="forbid"`), `importer.py`
  (.md+.json через python-frontmatter), `sampler.py` (веса), `db.py` (SQLite), `main.py` (FastAPI:
  `/api/graph|weights|interview|sessions…`).
- **Frontend** (`frontend/src/`): `App.tsx` (состояние, `buildNodes`, HUD, реестр `nodeTypes`),
  `layout.ts`, `types.ts`, `components/`, `report.ts`, `styles.css`.
- **Контент**: `content/<block>/*.md|*.json` + `content/weights.yaml`.
- **Тесты/прогон**: `backend/tests/test_app.py`, `frontend/smoke.mjs`, `./run.sh`, uvicorn :8000.

---

## Конвенции и грабли

- Ground truth — через `cat`/`grep`/`/api/graph`, НЕ через Read (контент нормализуется скриптами).
- Правки контента — через `python-frontmatter` (нормализованный формат).
- Рёбер не добавлять; теги только из 17 сквозных концептов (1–3 на ноду); difficulty base→senior;
  под-колонки через `subblock`.
- `Node` имеет `extra="forbid"` → новое поле ноды = правка `models.py` + `types.ts` + миграция контента.
- Новый тип ноды на канве = регистрация в `nodeTypes` (App.tsx).

---

## Verify (как доказать, что ничего не сломалось)

```bash
python3 .claude/skills/interview-verify/check_import.py          # import нод: 0 ошибок
cd backend && . .venv/bin/activate && python -m pytest -q        # backend-тесты
cd frontend && npm run build                                     # типы + бандл (если правка фронта)
cd frontend && npm run smoke                                     # headless smoke (нужен сервер :8000)
```

- **Когда что нужно:** правка только контента → import + pytest + smoke; правка `frontend/src` →
  ещё `npm run build`; правка `backend/app` → import + pytest.
- **Зелёный =** все шаги без ошибок, smoke печатает «ALL SMOKE CHECKS PASSED ✓».
- Переименовал ноду/тег/класс, на который опирается smoke — обнови `frontend/smoke.mjs`.

---

## Deploy (как фича попадает в прод)

- `trigger`: `merge-to-main` — деплой на сервер (порт 8800) срабатывает по merge в `main` (см. `DEPLOY.md`).
- `commands`: — (запускает CI, не `feature-ship`).
- `checks`: `curl -s -o /dev/null -w "%{http_code}" http://<host>:8800/` → 200.

`feature-ship` здесь только мёржит ветку-кандидат в `main` и проверяет healthcheck; команды деплоя — на CI.
