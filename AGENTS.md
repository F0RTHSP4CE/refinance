# Repository Guidelines

## Project Structure & Module Organization
- `api/app/`: FastAPI backend (`routes/`, `services/`, `models/`, `schemas/`, `tasks/`, `middlewares/`).
- `api/tests/`: pytest suite for API behavior and regressions.
- `ui-new/src/`: React + TypeScript frontend (`pages/`, `components/`, `api/`, `stores/`).
- `ui/app/`: legacy Flask/Jinja UI still shipped in Docker compose.
- `docs/`: architecture and auth notes. `docker-compose*.yml` defines `dev`, `prod`, and `ci` environments.

## Build, Test, and Development Commands
- `uv python install 3.12 && uv sync --dev`: install Python runtime and backend dependencies.
- `make dev`: run Docker services and start `ui-new` in dev mode.
- `make test`: boot the dev stack in background and run backend `pytest` in the `api` container.
- `make ci`: CI-equivalent API test run (`pytest -v -s --log-level DEBUG`) with teardown.
- `cd ui-new && npm run dev|build|lint|test:run|format:check`: frontend dev, build, lint, test, and formatting checks.

## Coding Style & Naming Conventions
- Python: 4-space indentation, Black formatting (88-char line length), isort with Black profile.
- Install hooks with `pre-commit install`, then run `pre-commit run --all-files` before PRs.
- Python naming: modules/functions in `snake_case`, classes in `PascalCase`.
- Frontend: function components only. ESLint forbids class components and `component.displayName`.
- Use named exports in app code (no default exports), and prefer the `@/` import alias.
- React component folders should follow `ComponentName/ComponentName.tsx` with a local `index.ts`.

## Testing Guidelines
- Backend tests belong in `api/tests/test_*.py`; shared fixtures live in `api/conftest.py`.
- Frontend tests use Vitest + Testing Library and must match `src/**/*.test.{ts,tsx}`.
- No explicit coverage threshold is enforced; add tests for behavior changes and edge cases.
- For UI logic changes, include at least one focused component or flow test.

## Commit & Pull Request Guidelines
- Current history favors concise, imperative commits, often with prefixes like `feat:`, `fix:`, or `wip:`.
- Prefer `type: short summary` (example: `fix: handle expired keepz token`).
- PRs should include: problem statement, change summary, test evidence (commands run), and screenshots for UI changes.
- Link related issues/tasks and call out config or migration impacts explicitly.
