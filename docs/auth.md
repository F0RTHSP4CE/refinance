
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
- `REFINANCE_DATABASE_URL`: PostgreSQL connection string (defaults to `postgresql://postgres:postgres@db:5432/refinance` when running via docker compose).

Testing locally:
1) Create `secrets.dev.env`:
```console
cp secrets.env.example secrets.dev.env
# set:
REFINANCE_SECRET_KEY=dev-secret-xxxx
REFINANCE_UI_URL=http://localhost:9000
REFINANCE_API_URL=http://localhost:8000
# Optional: set a real Telegram bot token if you want to receive login links in Telegram
REFINANCE_TELEGRAM_BOT_API_TOKEN=123456:ABC...
# Optional: override REFINANCE_DATABASE_URL if Postgres is running elsewhere
REFINANCE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/refinance
```
2) Start stack:
```console
make dev
```
3) Open UI `http://localhost:9000/auth/login`, enter an entity name that exists.
   - The seed includes `F0` and several system entities. To test personal login via Telegram, create your own entity and set `auth.telegram_id` to your Telegram numeric ID.
4) Check API logs for debug info:
```console
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f api
```
   - You will see whether `entity_found`, `token_generated`, and whether a Telegram message was sent.
5) If Telegram is configured, the bot will DM you a login button. If Telegram blocks button URLs, a fallback message with a bare link is sent.

Add user (entity) quickly:
1) Start dev stack: `make dev`
2) Add a new user using the Makefile helper (runs inside the API container):
```console
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
```console
curl -s -X POST -H 'Content-Type: application/json' -d '{"entity_name":"skywinder"}' http://localhost:8000/tokens/request
```
- `message_sent=false` usually means either:
  - `auth` is empty or has no `telegram_id` for the entity, or
  - `REFINANCE_TELEGRAM_BOT_API_TOKEN` is invalid, or
  - the bot cannot message your account (you have not started the bot in Telegram, or privacy settings block it).
- Check UI -> API call logs:
```console
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f ui
```
- Verify the bot token:
```console
TOKEN=<paste bot token>
curl -s https://api.telegram.org/bot${TOKEN}/getMe
```
  should return ok=true for a valid token.
