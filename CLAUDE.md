# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Everything runs in Docker; the host only needs `make`, `docker`, and (for editor support) `uv` + Python 3.12.

- `make dev` — build and run the full stack (api + ui + Postgres) with live code reload. API at http://localhost:8000/docs, UI at http://localhost:9000. Requires `secrets.dev.env` (copy from `secrets.env.example`).
- `make prod` — detached prod stack. Requires `secrets.prod.env`.
- `make test` — runs `pytest` inside the running `api` container. The stack must be up; the target brings it up detached if not.
- `make ci` — same as test but for CI: brings up the ci compose, runs `pytest -v -s --log-level DEBUG`, tears down. This is what GitHub Actions runs.
- `make add-entity NAME=<name> [TELEGRAM_ID=<id>] [ID=<id>]` — upsert an entity via `python -m app.scripts.add_entity` inside the api container.
- `make db-backup` / `make db-restore BACKUP_FILE=...` — pg_dump/restore against the current `ENV` (default `dev`).
- Run a single test: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api pytest tests/test_donation.py::ClassName::test_name`.

Local Python env (optional, for editor/typing): `uv python install 3.12 && uv sync --dev`, then point the IDE at `.venv`.

Lint/format is `black` + `isort` (profile=black) via pre-commit. `pre-commit install` after activating `.venv`.

## High-level architecture

Two services share one repo and one Python project (`pyproject.toml`):

- **`api/`** — FastAPI backend (port 8000). Owns all business logic, the database, and async background jobs.
- **`ui/`** — Flask "backend for frontend" (port 9000). Renders Jinja2 templates and forwards every action to the API via HTTP. It has no database access — `ui/app/external/refinance.py` is the only API client.

### Domain model

Everything in the system is one of four primitives, defined in `api/app/models/`:

- **Entity** — anything that can hold a balance (person, hackerspace, rent bill, fridge). Has free-form `auth` JSON (e.g. `{"telegram_id": 123}`) used by `TokenService` to deliver login links.
- **Transaction** — `(from_entity, to_entity, amount, currency, treasury)`. The atomic money movement; no negative amounts, no "delete" (corrections are inverse transactions).
- **Tag** — categorizes Entities and Transactions for search.
- **Treasury** — where the money physically lives (cash box, USDT wallet, Keepz). Specified on each Transaction.

**Balance** is not a stored model — it's the signed sum of transactions per (entity, currency), computed by `BalanceService` with an in-memory class-level cache (`BalanceService._cache`, `_treasury_cache`). The cache is invalidated by transaction writes and explicitly cleared between test classes in `conftest.py`.

### Bootstrap & seeding (no Alembic)

There are no real migrations — the `api/migrations/` directory is empty. Schema lives in SQLAlchemy models and is created at startup by `BaseModel.metadata.create_all()` in `api/app/db.py`. The same path then runs `seed_bootstrap_data()` which `session.merge`s a fixed set of tags/entities/treasuries (`api/app/seeding.py`) with hardcoded IDs (system entities use IDs 1–53, autoincrement starts at 100 for user-created rows). Seeding is gated by `DatabaseConnection._bootstrapped_urls` so it runs once per (process, database URL) — important to know if you change schema: there is no migration path, you either start fresh, hand-write SQL, or restore from a backup.

### API request flow

`api/app/app.py` is the composition root. It mounts every router in `api/app/routes/*.py` and starts four asyncio background tasks in `lifespan` (`invoice_auto_pay`, `keepz_poll`, `auto_exchange`, `balance_reminder` — see `api/app/tasks/`).

DI wiring lives in `api/app/dependencies/services.py`: `ServiceContainer` is a per-request lazy graph of every service. Routes depend on `get_<x>_service(container)` instead of constructing services themselves. This is also where service-to-service dependencies are resolved (e.g. `TransactionService` ↔ `InvoiceService` is bootstrapped via a deferred setter to break a cycle). When adding a new service, add a lazy property here and a corresponding `get_*_service` function rather than instantiating in the route.

`BaseService` (`api/app/services/base.py`) provides generic CRUD against any `BaseModel` and applies `BaseFilterSchema` (`comment ilike`, `created_before`, `created_after`) plus a model-specific `_apply_filters` hook. `BaseModel` requires `id`, `comment`, `created_at`, `modified_at` on every table.

Sessions are wrapped in `UnitOfWork` (`api/app/uow.py`): it delegates attribute access to the underlying `Session` and commits/rollbacks on context exit. `get_uow` is the dependency every service uses — don't `Depends(get_db)` directly.

Errors derive from `ApplicationError` (`api/app/errors/base.py`) and are caught by a global handler that returns JSON `{error_code, error, where}` with `http_code` (defaults to 418). `SQLAlchemyError` also has a global handler. Inside services, raise typed errors (e.g. `NotFoundError`, `TokenInvalid`) — don't return error responses.

Auth: `X-Token` header is a JWT signed with `REFINANCE_SECRET_KEY`. `middlewares/token.py:get_entity_from_token` is the route-level dependency that resolves a token to an `Entity`. Login flow is in `docs/auth.md`. POS endpoints use a separate `REFINANCE_POS_SECRET` (`middlewares/pos.py`). The global request-logging middleware (`app.py`) also decodes `x-token` and appends `X-Actor-Id` to non-GET responses.

Amounts are `Decimal` end-to-end. Serialization uses the custom `CurrencyDecimal` pydantic type in `api/app/schemas/base.py` so JSON always renders amounts as strings with sensible precision.

### UI request flow

`ui/app/app.py` registers a blueprint per domain (`controllers/<x>.py`), mostly mirroring the API routes. A `before_request` hook short-circuits `/auth`, `/donate`, `/static`, and `/style.css`; for everything else it requires `session["token"]`, calls `GET /entities/me` and `GET /balances/<id>`, and puts the results on `flask.g`. CSRF tokens and form `submit` keys are stripped from outgoing API payloads by `RefinanceAPI._clean_nested_dicts`.

Templates extend `templates/base.jinja2`. Static CSS is hand-rolled (per-feature files in `ui/app/static/`); `style.css` is a Jinja-rendered route with a cache-buster token.

## Testing

`api/conftest.py` provides class-scoped fixtures. `test_app` creates a **fresh Postgres database per test class** (DSN from `REFINANCE_TEST_DATABASE_URL`, defaulting to the dockerized `db` service), runs `create_tables` + `seed_bootstrap_data`, exposes a hidden `GET /tokens/{entity_id}` route used only by tests to mint tokens, and tears the database down at class exit. It also clears `BalanceService._cache` between classes — if you add another module-level cache, clear it here too.

Tests must run inside the api container (`make test`); the default test DSN points at the `db` hostname only resolvable inside the docker network. Per the README, most tests are LLM-generated from routes + schemas — treat coverage as broad-but-shallow.

## Environment variables

Configuration is `dataclass`-based (`api/app/config.py`, `ui/app/config.py`) — all values come from `REFINANCE_*` env vars loaded via `secrets.{dev,prod}.env`. See `secrets.env.example` for the full list. Notable ones beyond the auth doc:

- `REFINANCE_FEE_PRESETS` — JSON list of `{tag_id, currency, amount}` overrides for monthly fees (defaults in `DEFAULT_FEE_PRESETS`).
- `REFINANCE_DONATION_MIN_AMOUNT` / `REFINANCE_DONATION_MAX_AMOUNT` — guest donation limits (enforced in both api and ui).
- `REFINANCE_KEEPZ_*`, `REFINANCE_CRYPTAPI_ADDRESS_*` — deposit provider config for the polling tasks.
