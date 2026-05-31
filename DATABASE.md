# Database Setup

## First-time setup

Start the local database:

```sh
docker compose -f docker-compose.dev.yaml up -d
```

Create the database, then run migrations:

```sh
make db-create
make migrate
```

Expected output:

```
Running Alembic migrations...
uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> da17fa6f2667, initial
```

## Common commands

| Command | Description |
|---|---|
| `make db-up` | Start local postgres |
| `make db-down` | Stop local postgres |
| `make db-create` | Create the application database if it doesn't exist |
| `make migrate` | Apply all pending migrations |
| `make migrate-auto name=create_my_table` | Autogenerate a migration from model changes |
| `make rollback` | Undo the last migration |
