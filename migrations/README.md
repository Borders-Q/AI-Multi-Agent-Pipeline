# SkyT database migrations

Migrations are append-only and target MySQL 8.0+. Each migration is recorded in
`schema_migrations` and should be applied once before the application starts.

The current application keeps the legacy bootstrap in `db.init_db()` for
backwards-compatible Windows single-machine startup. New schema changes belong
in this directory and must use an idempotent migration before the bootstrap is
removed.
