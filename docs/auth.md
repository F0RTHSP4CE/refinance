
### how auth works (dev)
Flow overview:
- UI calls `POST /tokens/send` with `entity_name`.
- API finds the `Entity` by name and generates a signed token.
- API builds a link `${REFINANCE_UI_URL}/auth/token/<token>` and tries to send it through providers in `Entity.auth`.
- If `auth.telegram_id` is present, API uses the Telegram bot to send a button with the login link.
- When you click the link, UI saves the token in session and you are logged in.

Environment variables used:
- `REFINANCE_SECRET_KEY`: JWT signing key for tokens.
- `REFINANCE_UI_URL`: Used to construct login links.
- `REFINANCE_API_URL`: Used by deposit callbacks.
- `REFINANCE_TELEGRAM_BOT_API_TOKEN`: Telegram bot token to deliver login links.
- `REFINANCE_TELEGRAM_BOT_USERNAME`: Telegram bot username used by the runtime Telegram sign-in widget/button.
- `REFINANCE_DATABASE_URL`: PostgreSQL connection string (defaults to `postgresql://postgres:postgres@db:5432/refinance` when running via docker compose).

Testing locally:
1) Create `secrets.dev.env`:
```console
cp secrets.env.example secrets.dev.env
# set:
REFINANCE_SECRET_KEY=dev-secret-xxxx
REFINANCE_UI_URL=http://localhost:5173
REFINANCE_API_URL=http://localhost:8000
# Optional: set a real Telegram bot token if you want to receive login links in Telegram
REFINANCE_TELEGRAM_BOT_API_TOKEN=123456:ABC...
# Required for the Telegram widget button in ui-new
REFINANCE_TELEGRAM_BOT_USERNAME=refinance_bot
# Optional: override REFINANCE_DATABASE_URL if Postgres is running elsewhere
REFINANCE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/refinance
```
2) Start stack:
```console
make dev
```
3) Open UI `http://localhost:5173/sign-in`, enter an entity name that exists.
   - The seed includes `F0` and several system entities. To test personal login via Telegram, create your own entity and set `auth.telegram_id` to your Telegram numeric ID.
   - The legacy Flask UI still runs on `http://localhost:9000`, but Telegram auth in `ui-new` expects `REFINANCE_UI_URL` to point to `http://localhost:5173`.
   - If the Telegram widget shows `Bot domain invalid` on localhost, use the username flow for local testing or expose `ui-new` on a public HTTPS URL and register that URL for the bot in BotFather.
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
- UI: after login, go to `Entities` to add or edit entities. To enable Telegram sign-in for yourself, sign in once by username and then use `Profile -> Telegram login` to connect your Telegram account.
- CLI: use `make add-entity` to upsert by name or id. Under the hood it calls `python -m app.scripts.add_entity` inside the API container.
- Deleting entities: not supported yet in the API/UI.

Troubleshooting:
- If the login page shows failure, call the API directly to see details:
```console
curl -s -X POST -H 'Content-Type: application/json' -d '{"entity_name":"skywinder"}' http://localhost:8000/tokens/send
```
- `message_sent=false` usually means either:
  - `auth` is empty or has no `telegram_id` for the entity, or
  - `REFINANCE_TELEGRAM_BOT_API_TOKEN` is invalid, or
  - the bot cannot message your account (you have not started the bot in Telegram, or privacy settings block it).
- Check UI -> API call logs:
```console
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f ui-new
```
- Verify the bot token:
```console
TOKEN=<paste bot token>
curl -s https://api.telegram.org/bot${TOKEN}/getMe
```
  should return ok=true for a valid token.
- If the Telegram widget itself says `Bot domain invalid`, Telegram is rejecting the current page origin for web login. This repo uses the Telegram website login widget, so the page URL must be registered for the bot. On local `localhost` development, prefer the username login flow or use a public HTTPS tunnel and point `REFINANCE_UI_URL` at that same origin.
