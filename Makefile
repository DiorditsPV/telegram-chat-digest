# Гейт качества — единый источник правды (локально и в CI: `make check`).
.PHONY: check lint format format-check typecheck test

check: lint format-check typecheck test ## весь гейт

lint: ## ruff: статический анализ
	ruff check .

format-check: ## ruff: проверка форматирования (без правок)
	ruff format --check .

format: ## ruff: применить форматирование
	ruff format .

typecheck: ## mypy: типы (telethon/yaml игнорятся через pyproject)
	mypy scripts

test: ## pytest: весь набор (чистые тесты, без сети/Telegram)
	pytest
