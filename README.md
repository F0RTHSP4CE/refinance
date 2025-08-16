# refinance
![logo](docs/refinance-logo.jpg)

refined financial system for a hackerspace. simple by design.

## architecture

### entity
anything that can send or receive money: human, donate-box, rent, utility.

### transaction
move X from A to B. supports all currencies.
- non-confirmed
- confirmed

### balance
sum of all transactions. both confirmed and not. separated.

### tags
mark entities and transactions for quick search.

## authentication
- you can request a login link with your entity name, telegram id, signal id or whatever.
- login link will be sent to all available destinations (telegram, signal, email, etc)
- new login link does not revoke old ones, so no one can deauthenticate you.

### how auth works (dev)
Flow overview:
- UI calls `POST /tokens/request` with one of: `entity_id`, `entity_name`, `entity_telegram_id`.
- API finds the `Entity` by the first matching criterion and generates a signed token.
- API builds a link `${REFINANCE_UI_URL}/auth/token/<token>` and tries to send it through providers in `Entity.auth`.
- If `auth.telegram_id` is present, API uses the Telegram bot to send a button with the login link.
- When you click the link, UI saves the token in session and you are logged in.

Environment variables used:
- `REFINANCE_SECRET_KEY`: JWT signing key for tokens.
- `REFINANCE_UI_URL`: Used to construct login links.
- `REFINANCE_API_URL`: Used by deposit callbacks.
- `REFINANCE_TELEGRAM_BOT_API_TOKEN`: Telegram bot token to deliver login links.

Testing locally:
1) Create `secrets.dev.env`:
```
cp secrets.env.example secrets.dev.env
# set:
REFINANCE_SECRET_KEY=dev-secret-xxxx
REFINANCE_UI_URL=http://localhost:9000
REFINANCE_API_URL=http://localhost:8000
# Optional: set a real Telegram bot token if you want to receive login links in Telegram
REFINANCE_TELEGRAM_BOT_API_TOKEN=123456:ABC...
```
2) Start stack:
```
make dev
```
3) Open UI `http://localhost:9000/auth/login`, enter an entity name that exists.
   - The seed includes `F0` and several system entities. To test personal login via Telegram, create your own entity and set `auth.telegram_id` to your Telegram numeric ID.
4) Check API logs for debug info:
```
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f api
```
   - You will see whether `entity_found`, `token_generated`, and whether a Telegram message was sent.
5) If Telegram is configured, the bot will DM you a login button. If Telegram blocks button URLs, a fallback message with a bare link is sent.

Add user (entity) quickly:
1) Start dev stack: `make dev`
2) Add a new user using the Makefile helper (runs inside the API container):
```
make add-entity NAME=<name> [TELEGRAM_ID=<numeric_id>] [ID=<explicit_id>]
# examples:
make add-entity NAME=alice
make add-entity NAME=alice TELEGRAM_ID=123456789
```
3) On the login page, enter `<name>`. If `TELEGRAM_ID` was set and the bot token is valid, you will receive a Telegram login link.

Entity & user management:
- UI: after login, go to `Entities` to add or edit entities. You can set `Auth → Telegram ID` (from `@myidbot`) and tags.
- CLI: use `make add-entity` to upsert by name or id. Under the hood it calls `python -m app.scripts.add_entity` inside the API container.
- Deleting entities: not supported yet in the API/UI.

Troubleshooting:
- If the login page shows failure, call the API directly to see details:
```
curl -s -X POST -H 'Content-Type: application/json' -d '{"entity_name":"skywinder"}' http://localhost:8000/tokens/request
```
- `message_sent=false` usually means either:
  - `auth` is empty or has no `telegram_id` for the entity, or
  - `REFINANCE_TELEGRAM_BOT_API_TOKEN` is invalid, or
  - the bot cannot message your account (you have not started the bot in Telegram, or privacy settings block it).
- Check UI -> API call logs:
```
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f ui
```
- Verify the bot token:
```
TOKEN=<paste bot token>
curl -s https://api.telegram.org/bot${TOKEN}/getMe
```
  should return ok=true for a valid token.

## production

use `secrets.prod.env` for production secrets. start from the example file:

```console
cp secrets.env.example secrets.prod.env
# then edit secrets.prod.env (set real domain URLs and database URL)
```

```console
make prod-daemon
```

API: http://0.0.0.0:8000/docs
UI: http://0.0.0.0:9000

## development

### environment setup (first time)
create `secrets.dev.env` for development variables. see `secrets.env.example` as a reference. docker compose loads this file automatically in dev.

```console
cp secrets.env.example secrets.dev.env
```

### create local environment with all dependencies
```console
uv python install 3.12
uv sync --dev
```

open project in vscode, <kbd>F1</kbd> `python.setInterpreter`, select `.venv` (workspace)

if you need to change project deps:
```console
uv add packagename
uv remove packagename
uv sync
```

install pre-commit hook
```
source ./.venv/bin/activate
pre-commit install
```

### tests
```
make test
```

### run backend & frontend with live code reload
```console
make dev
```
open http://localhost:8000/docs and http://localhost:9000

### secrets files overview
- `secrets.dev.env`: used by `make dev` (docker-compose.dev.yml)
- `secrets.prod.env`: used by `make prod`/`make prod-daemon` (docker-compose.prod.yml)
- `secrets.env.example`: used by CI and as a template; do not put secrets here

## todo release
- [x] base classes
- [x] errors
- [x] unit tests
- [x] complex search
- [x] pagination
- [x] tags
- [x] transactions
- [x] balances
- [x] balance cache
- [x] date range search
- [x] payment splits
- [x] multiple auth providers
- [x] docker
- [x] authentication?
- [x] pytest ci
- [x] generic deposit service
- [x] usdt top-up
- [x] currency exchange
- [x] unit of work?
- [x] fixed amount participation in split
- [x] add split participants by a tag
- [x] ~~grafana~~, statistics
- [x] treasuries
- [x] logging
- [x] postgres

## todo techdebt
- [ ] migrations
- [x] pass tags as a list, not as add/delete operations
    - [x] fix ui tag management
- [x] misc validation of amounts (>0.00)
- [ ] improve split ux
- [x] make a uniform deposit api CRUD, provider should be enum
- [ ] update all boolean attrs to status enums
- [ ] mobile ui
- [ ] rename base to common where applicable
- [ ] ~~remove _in and _out postfixes for entities~~ not needed
- [ ] remove base service class

## todo future features
- [ ] permissions?
- [ ] deposit ui
- [ ] donation categories (entities?)
- [ ] easy payment urls
- [ ] card processing

## tests notice
tests are mostly autogenerated by llm, given the route and schema. human review would be beneficial.

## license
MIT
