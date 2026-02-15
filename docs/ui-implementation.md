# Refinance UI — Implementation Overview

This document describes how the frontend (UI) works and how it integrates with the backend (API).

---

## Architecture Summary

| Layer | Tech | Purpose |
|-------|------|---------|
| **UI Server** | Flask (Python) | Renders pages, handles routes, proxies to API |
| **Templating** | Jinja2 | Server-side HTML generation |
| **Interactivity** | HTMX + vanilla JS | Partial updates, search, minimal client logic |
| **Styling** | CSS (static/style.css) | Layout and appearance |
| **Backend API** | FastAPI | REST JSON API (separate service) |

**Pattern:** Classic server-rendered MVC. The UI is a **thin BFF (Backend-for-Frontend)** that talks to the refinance API over HTTP and renders HTML.

---

## Directory Structure

```
ui/
├── app/
│   ├── app.py              # Flask app, routes, before_request, globals
│   ├── config.py           # REFINANCE_API_BASE_URL, presets, entity/tag IDs
│   ├── schemas.py          # Dataclasses for API responses (Entity, Transaction, etc.)
│   ├── controllers/       # Blueprints (routes + handlers)
│   │   ├── auth.py
│   │   ├── entity.py
│   │   ├── transaction.py
│   │   ├── invoice.py
│   │   ├── deposit.py
│   │   ├── split.py
│   │   ├── tag.py
│   │   ├── treasury.py
│   │   ├── exchange.py
│   │   ├── fee.py
│   │   ├── stats.py
│   │   └── index.py
│   ├── external/
│   │   └── refinance.py    # HTTP client for the API
│   ├── middlewares/
│   │   └── auth.py        # token_required decorator
│   ├── exceptions/
│   │   └── base.py        # ApplicationError
│   ├── static/
│   │   ├── style.css
│   │   ├── js/
│   │   │   ├── entitySelector.js   # Entity search → ID sync
│   │   │   ├── dateToggle.js
│   │   │   ├── mobileMenu.js
│   │   │   └── multiSelect.js
│   │   └── images/
│   └── templates/
│       ├── base.jinja2    # Layout, nav, HTMX
│       ├── form.jinja2    # Generic form render macro
│       ├── auth/
│       ├── entity/
│       ├── transaction/
│       ├── invoice/
│       ├── deposit/
│       ├── split/
│       ├── tag/
│       ├── treasury/
│       ├── exchange/
│       ├── fee/
│       ├── stats/
│       └── widgets/       # Reusable macros (pagination, entity selector, etc.)
└── Dockerfile
```

---

## Backend Integration

### API Client (`app/external/refinance.py`)

- **Class:** `RefinanceAPI`
- **Base URL:** `REFINANCE_API_BASE_URL` (default `http://api:8000` when running in Docker)
- **Auth:** Sends `X-Token` header with the session token (JWT from `/auth/token/<token>`)

**Usage:**

```python
api = get_refinance_api_client()  # Uses session["token"]
r = api.http("GET", "entities", params={"skip": 0, "limit": 50})
data = r.json()
```

- Cleans `csrf_token` and `submit` from request bodies
- Raises `ApplicationError` on non-200 responses
- Logs all requests and responses

### API Endpoints Used (examples)

| UI Feature | API Endpoints |
|------------|---------------|
| Auth | `POST /tokens/send`, `GET /entities/me` |
| Entities | `GET/POST/PATCH/DELETE /entities`, `GET /entities/{id}/cards`, `GET /balances/{id}` |
| Transactions | `GET/POST/PATCH/DELETE /transactions` |
| Invoices | `GET/POST/PATCH/DELETE /invoices` |
| Tags | `GET /tags` |
| Treasuries | `GET /treasuries` |
| Stats | `GET /stats/entity/{id}` |
| Splits | `GET/POST /splits`, etc. |
| Deposits | `GET/POST /deposits`, etc. |

All API routes require the `X-Token` header (except token request and token auth).

---

## Authentication Flow

1. **Login page** (`/auth/login`): User enters entity name → `POST /tokens/send` to API.
2. **Token delivery**: API sends login link via Telegram, or returns `login_link` in dev mode.
3. **Token auth** (`/auth/token/<token>`): UI stores token in Flask session, redirects to home.
4. **Before each request** (`app.before_request`):
   - Skips auth for `/auth`, `/static`.
   - Calls `GET entities/me` and `GET balances/{id}` to load `g.actor_entity` and `g.actor_entity_balance`.
   - If 401 or missing token → redirect to `/auth/login`.

### Session

- Token stored in `session["token"]`.
- Session is permanent (30 days), SameSite=Lax.
- `token_required` decorator ensures session has token before controller runs.

---

## Request Flow (Typical Page)

```
Browser → Flask route → token_required → get_refinance_api_client()
                                    → api.http("GET", "entities", params=...)
                                    → API returns JSON
                                    → Controller builds dataclasses
                                    → render_template("entity/list.jinja2", ...)
                                    → Jinja2 renders HTML
                                    → Response to browser
```

---

## Templates & Interactivity

### Base Template (`base.jinja2`)

- Loads `normalize.css`, `style.css`, **HTMX** (`htmx.org@1.6.1`).
- Includes mobile menu (JS in `mobileMenu.js`).
- Blocks: `body_class`, `title`, `content`.

### HTMX Usage

- **Entity search:** `hx-get="/hx/search"` on input with `hx-trigger="input changed delay:250ms"`.
- **Target:** `#{{ prefix }}_search_results` — replaced with search results partial.
- **Endpoint:** `GET /hx/search?name=...` → returns `widgets/hx_entity_selector.jinja2` (list of entity links).

### Entity Selector Widget

- Macro: `entity_selector(prefix, initial_name, initial_id)`.
- Search input + hidden ID input.
- `entitySelector.js`:
  - On ID change: fetch `/hx/entity-name/<id>` → update name.
  - On search result click: set name + ID, clear results.

### Form Rendering

- `form.jinja2`: `render_form(form, except=('csrf_token'))` — table-based form layout.
- Uses **Flask-WTF** for CSRF and validation.

---

## Controllers Pattern

Each controller:

1. Uses `@token_required` for protected routes.
2. Gets `api = get_refinance_api_client()`.
3. Calls `api.http(METHOD, "endpoint", params=..., data=...)`.
4. Parses JSON into dataclasses from `app.schemas`.
5. Renders a Jinja2 template with the data.

Example (entity list):

```python
@entity_bp.route("/")
@token_required
def list():
    api = get_refinance_api_client()
    response = api.http("GET", "entities", params={"skip": skip, "limit": limit, **filters}).json()
    entities = [Entity(**x) for x in response["items"]]
    return render_template("entity/list.jinja2", entities=entities, ...)
```

---

## Configuration (`config.py`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `REFINANCE_API_BASE_URL` | `http://api:8000` | API base URL |
| `FRIDGE_PRESETS` | `[{"amount": 5, "currency": "GEL", ...}]` | Fridge shortcut presets |
| `COFFEE_PRESETS` | Similar | Coffee shortcut presets |
| `TAG_IDS` | fee, deposit, withdrawal, resident, member | Tag IDs for shortcuts |
| `ENTITY_IDS` | f0, fridge, coffee | Entity IDs for shortcuts |

Overridden via env vars (e.g. in `secrets.dev.env`).

---

## Running the UI

- **Docker:** `make dev` — UI runs on port 9000, API on 8000.
- **API URL:** In Docker, UI uses `http://api:8000` (service name). For local dev without Docker, set `REFINANCE_API_BASE_URL=http://localhost:8000`.

---

## Summary

| Aspect | Implementation |
|--------|----------------|
| **Rendering** | Server-side (Jinja2) |
| **State** | Session (token), `g` (actor + balance) |
| **API** | HTTP client with `X-Token`, JSON in/out |
| **Interactivity** | HTMX + 4 small JS modules |
| **Forms** | Flask-WTF, CSRF, server validation |
| **Styling** | Single CSS file, normalize.css |

No SPA framework, no bundler. The UI is a traditional server-rendered app that uses the FastAPI backend as a data source.
