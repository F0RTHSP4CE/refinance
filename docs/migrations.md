# schema migrations

Schema is managed by [Alembic](https://alembic.sqlalchemy.org/). Migration scripts live in `api/migrations/versions/`.

## how it works

- The API container's entrypoint (`api/entrypoint.sh`) runs `alembic upgrade head` and `python -m app.scripts.seed` before starting uvicorn. Fresh environments build the schema automatically; existing ones get any pending revisions applied.
- The `db` service has a `pg_isready` healthcheck. The API container waits for it (`depends_on: condition: service_healthy`) so migrations never run against a not-yet-ready Postgres.
- Tests use `conftest.py`'s `_temporary_database` fixture, which creates a one-off DB per test class via `BaseModel.metadata.create_all`. Tests do not go through Alembic — they trade fidelity for speed.
- CI catches drift via `alembic check` after pytest in `make ci`. If a model changes without a matching revision, CI fails.

## creating a new migration

1. Edit the relevant model in `api/app/models/`.
2. With the dev stack up (`make dev`), generate a revision:
   ```console
   make migration NAME=add_user_email
   ```
   This calls `alembic revision --autogenerate` inside the API container. A new file appears in `api/migrations/versions/`.
3. **Review the generated file by hand.** Autogenerate is not authoritative — see caveats below.
4. Apply locally:
   ```console
   make migrate
   ```
5. Commit both the model change and the revision file in the same commit.

## applying migrations

Normally you don't need to — the API entrypoint runs `alembic upgrade head` on every container start. To apply manually:

```console
make migrate                  # dev (default)
make ENV=prod migrate         # prod
```

## rolling back

```console
make migrate-down                    # roll back one revision
make ENV=prod migrate-down           # same on prod
```

For a specific revision: `docker compose ... exec api alembic downgrade <rev_id>`.

Rollback only works if the revision's `downgrade()` is correct — autogenerate produces it, but data-destructive operations (drop column, drop table) may need manual review for prod safety.

## inspecting state

```console
make migrate-history                                          # full history
docker compose ... exec api alembic current                   # currently applied revision
docker compose ... exec api alembic check                     # detect model/DB drift
docker compose ... exec api alembic show <rev_id>             # details of one revision
```

## stamping an existing database

When adopting Alembic on a DB that already has the schema (e.g. existing prod), `alembic upgrade head` would try to `CREATE TABLE` on tables that already exist and fail. Instead, mark the DB as already-migrated without running DDL:

```console
make ENV=prod up-detached
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec api alembic stamp head
```

After stamping, `alembic current` should report the head revision. Subsequent deploys behave normally.

**Stamp prod once, before the entrypoint-with-migrations image rolls out.** If you deploy the new image first, the entrypoint will try to run `alembic upgrade head` against an unstamped prod and fail to start the API.

Recommended order for the prod cutover:
1. Take a backup: `make ENV=prod db-backup`.
2. Pull the new code.
3. Run `alembic stamp head` in a one-off container (`docker compose ... run --rm --entrypoint sh api -c 'alembic stamp head'`) — or stop entrypoint via override and run interactively.
4. Deploy: `make prod`. Entrypoint now sees the DB at head, `alembic upgrade head` is a no-op, API starts.

## resolving revision conflicts

When two branches each add a revision off the same parent, you get two heads:

```console
docker compose ... exec api alembic heads
# rev_a
# rev_b
```

Merge them with a merge revision:

```console
docker compose ... exec api alembic merge -m "merge rev_a and rev_b" rev_a rev_b
```

Commit the merge revision. `alembic upgrade head` afterwards applies both branches in order.

## autogenerate caveats

Autogenerate compares model metadata against the live DB. It catches added/removed tables, columns, indexes, FKs, unique constraints, type changes, and server defaults (we have `compare_type=True, compare_server_default=True` in `env.py`). It **does not** catch:

- **Renames.** A renamed column shows up as `drop_column` + `add_column`, which loses data. Always rewrite renames as `op.alter_column(..., new_column_name=...)` by hand.
- **Check constraints, partial indexes, function-based indexes** — review and add manually.
- **Postgres enum value changes.** Adding a value to an enum requires `op.execute("ALTER TYPE ... ADD VALUE ...")`. Removing or renaming values requires creating a new enum, migrating data, and dropping the old one.
- **Data migrations.** If a schema change requires backfilling rows, write the data migration explicitly with `op.execute(...)` or `op.get_bind()` + SQLAlchemy core in the same revision.

Always read the generated revision file before committing. `pass` in `upgrade()` is a hint that autogenerate found nothing — fine for empty baselines, suspect otherwise.

## seeding

Bootstrap data (system entities, default tags, treasuries) is seeded by `python -m app.scripts.seed`, called from the entrypoint after migrations. The seeder is idempotent (`session.merge`), so re-running it on every container start is safe.

`SEEDING` lives in `api/app/seeding.py`. To add a new system entity or tag, edit that file and restart the API.
