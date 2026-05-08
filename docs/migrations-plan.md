# Миграции: план интеграции Alembic

Документ-план для перевода проекта с `BaseModel.metadata.create_all()` на полноценную систему миграций. Если работа прервётся — открывай этот файл, сверяйся с чек-листом прогресса и продолжай с нужного шага.

## Контекст: почему это нужно

Сейчас схема создаётся одним вызовом `BaseModel.metadata.create_all(bind=self.engine)` в `api/app/db.py:46`. Последствия:

- `create_all` не меняет существующие таблицы → любое изменение модели на проде даёт рассинхрон код/БД.
- Прод обновляется ручным SQL (см. `docs/invoice_id.sql` — типичный пример «теневой миграции»).
- Нет истории схемы, нет отката, нет возможности воспроизвести прод-схему в dev.
- Тесты создают БД с нуля → апгрейд-сценарии вообще не покрыты.

Цель — Alembic как стандарт для SQLAlchemy: поэтапное изменение схемы, ревью, откат, drift-check в CI.

## Прогресс

Отмечай галочками по мере выполнения. Если шаг частично сделан — добавь короткую пометку.

- [x] **1. Установка и каркас** — `uv add alembic`, `alembic init migrations` в `api/`
- [x] **2. Настройка `env.py`** — DB URL из `app.config`, импорт всех моделей, `compare_type=True`
- [x] **3. Baseline-ревизия** — `alembic revision --autogenerate -m "baseline"` + ручной ревью (rev `976049ef36a9_baseline.py`)
- [ ] **4. Стамп существующих БД** — `alembic stamp head` на проде. Dev застамплен и потом пересоздан с нуля при тесте entrypoint. Прод — операционный шаг, runbook в `docs/migrations.md`.
- [x] **5. Удаление `create_all` из прод-пути** — чистим `api/app/db.py`, выносим сидинг в `scripts/seed.py`
- [x] **6. Запуск миграций при старте** — entrypoint API делает `alembic upgrade head` перед uvicorn + healthcheck на db
- [x] **7. Тесты** — оставляем `create_all` для unit-тестов, добавляем `alembic check` в `make ci`
- [x] **8. Обработка `docs/invoice_id.sql`** — удалён (содержимое зашито в baseline)
- [x] **9. Makefile-цели** — `make migrate`, `make migration NAME=...`, `make migrate-down`, `make migrate-history`
- [x] **10. Документация** — раздел в `README.md` + `docs/migrations.md` с runbook'ом

## Решения, принятые заранее

- **Расположение:** `api/migrations/` (рядом с `app/`), `api/alembic.ini` в корне `api/`. Alembic видит модели через `app.models.*` и работает в том же контейнере, что и API.
- **DB URL:** берём из существующего `app.config.Config.database_url`, не дублируем в `alembic.ini`. В `env.py` импортируем `get_config()` и подставляем URL программно.
- **Sync, не async:** текущий `db.py` синхронный → используем `alembic init migrations` без `-t async`.
- **Тесты:** оставляем `create_all` (быстро, изолированно). Прод и dev переходят на миграции. В CI отдельный job проверяет, что `alembic upgrade head` на чистой БД даёт ту же схему, что модели.
- **SQLite:** существующая поддержка в `db.py` сохраняется (для тестов/локального запуска без docker). Alembic-окружение работает с PostgreSQL.

## Шаги

### 1. Установка и каркас (1 коммит)

```console
uv add alembic
cd api && alembic init migrations
```

Структура:
```
api/
  alembic.ini
  migrations/
    env.py
    script.py.mako
    versions/
```

### 2. Настройка `env.py`

Ключевые правки:
- `from app.config import get_config` → `config_obj.database_url` подставляется в `config.set_main_option("sqlalchemy.url", ...)`.
- `from app.models.base import BaseModel` + импорт всех модулей моделей (`entity`, `transaction`, `tag`, `treasury`, `split`, `invoice`, `deposit`) → `target_metadata = BaseModel.metadata`.
- `compare_type=True`, `compare_server_default=True` в `context.configure(...)` — autogenerate ловит изменения типов и дефолтов.
- `include_schemas=False`, `render_as_batch=False` (PG не требует batch mode).

### 3. Baseline-ревизия

```console
cd api && alembic revision --autogenerate -m "baseline"
```

Создаст ревизию с описанием **всей текущей схемы как есть**, например `versions/20260508_xxxx_baseline.py`.

**Обязательный ручной ревью.** Проверить:
- Все таблицы, индексы, FK, уникальные констрейнты на месте.
- Enum `invoice_status` создаётся корректно (PG-specific — Alembic должен сгенерировать `sa.Enum(..., name="invoice_status")`).
- Сравнить с `pg_dump --schema-only` действующего прода. Расхождения (например, `invoice_id` в `transactions` из `docs/invoice_id.sql`, который уже применён руками) — поправить в ревизии руками.

### 4. Стамп существующих БД

На действующих окружениях (prod + любые dev-БД с данными):
```console
make ENV=prod alembic stamp head
```

`stamp` **только записывает** ревизию в `alembic_version`, **не выполняя DDL**. Прод-схема уже соответствует baseline → стампим.

Чистые dev-БД (новые `make dev` с пустым volume) — Alembic выполнит baseline как обычно при `upgrade head`.

### 5. Удаление `create_all` из прод-пути

В `api/app/db.py`:
- Убрать вызов `self.create_tables()` из `__init__`.
- `create_tables()` оставить как метод — используется тестами через фикстуру.
- `seed_bootstrap_data()` продолжает работать (идемпотентный, `session.merge`). Перенести его вызов **после** `alembic upgrade head`, не в `__init__` engine'а.
- Убрать `_bootstrapped_urls` cache — после переноса инициализации в startup эта оптимизация не нужна.

### 6. Запуск миграций при старте

Два варианта, выбран **6a**:

**6a. Pre-start hook в Dockerfile/entrypoint API:**
- Добавить `entrypoint.sh` в `api/`: `alembic upgrade head && python -m app.scripts.seed && exec uvicorn ...`.
- Один процесс при старте накатывает миграции и сидит данные. Несколько реплик безопасно — Alembic берёт advisory lock в PG.

**6b. Отдельный one-shot сервис в docker-compose** (отброшено как избыточное):
- `migrator` сервис, который выполняет `alembic upgrade head && python -m app.scripts.seed` и завершается.
- API зависит через `depends_on: condition: service_completed_successfully`.

Сидинг выносим в `app/scripts/seed.py` — вытащить `seed_bootstrap_data` из `db.py` в отдельный CLI-скрипт.

### 7. Тесты

- `conftest.py` продолжает использовать `BaseModel.metadata.create_all(engine)` для in-memory SQLite — быстро.
- Отдельный CI-job `migrations-check`:
  ```console
  make ENV=ci up-detached
  docker compose ... exec api alembic upgrade head
  docker compose ... exec api alembic check
  ```
  `alembic check` (1.9+) сравнивает текущую модель с накатанной схемой и падает, если есть расхождения. Ловит «забыл сгенерить ревизию».

### 8. Обработка `docs/invoice_id.sql`

Файл — историческая ручная миграция, уже применённая в проде. После стампа baseline она «зашита» в baseline-ревизию. Удаляем или переносим в `migrations/legacy/` с README, что это исторический артефакт и запускать его не нужно.

### 9. Makefile-цели

```makefile
migrate: ENV ?= dev
migrate:
	$(COMPOSE) exec api alembic upgrade head

migration: ENV = dev
migration:
	@if [ -z "$(NAME)" ]; then echo "Usage: make migration NAME=<short_desc>"; exit 1; fi
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(NAME)"

migrate-down: ENV ?= dev
migrate-down:
	$(COMPOSE) exec api alembic downgrade -1

migrate-history: ENV ?= dev
migrate-history:
	$(COMPOSE) exec api alembic history --verbose
```

### 10. Документация

- Короткий раздел в `README.md` → `schema migrations`: как создать ревизию, как накатить, что делает `make migrate`.
- `docs/migrations.md` с разовыми инструкциями для команды: «как застампить существующую БД», «как откатиться», «как разрешить конфликт ревизий при merge».

## Порядок коммитов / PR'ов

Каждый PR независим и откатывается отдельно. Между шагом 1 и 3 проект продолжает работать на `create_all` без регресса.

1. **chore: add alembic** — установка, `env.py`, пустые `versions/`, baseline-ревизия, Makefile-цели. Ничего не вызывается автоматически — миграции опциональны.
2. **chore: stamp existing environments** — операционный шаг (не код), runbook в `docs/migrations.md`. Прод стампится.
3. **refactor(db): remove create_all from prod path** — `db.py` чистится, сидинг в `scripts/seed.py`, entrypoint делает `alembic upgrade head`. Тесты не трогаем.
4. **chore: drop legacy invoice_id.sql** — после стампа всех окружений.
5. **ci: add migrations check** — `alembic check` в CI.

## Риски и на что смотреть

- **Autogenerate не идеален.** Не ловит: переименования таблиц/колонок (видит как drop+add → потеря данных), check constraints, частично — server-side defaults. Каждую ревизию ревьюим глазами.
- **Enum в PG.** Изменение значений enum (`invoice_status`) требует ручного `op.execute("ALTER TYPE ...")`, autogenerate этого не делает.
- **Стамп прода.** Если baseline-ревизия не точно соответствует тому, что в проде → следующая ревизия упадёт. Перед стампом: `pg_dump --schema-only` прод-БД и сравнить с тем, что генерит `alembic upgrade head` на пустой БД. Расхождения — поправить baseline руками до стампа.
- **Сидинг и миграции.** Если сидинг создаёт записи, которые потом меняются миграциями, нужен правильный порядок. Сейчас `SEEDING` — справочные данные, проблем быть не должно.

## Где остановились

- **Дата:** 2026-05-08
- **Статус:** все шаги кроме #4 (стамп прода) выполнены на ветке `feat-alembic`. Ветка готова к ревью + PR'ам. Изменения не закоммичены — staging area содержит только `git rm docs/invoice_id.sql`.
- **Следующий шаг:** разбить изменения на PR'ы по плану (см. «Порядок коммитов / PR'ов» выше) и запланировать стамп прода (runbook в `docs/migrations.md` → раздел «stamping an existing database»).
