# Database and upgrades

PostgreSQL stores users and owner-scoped log records. Records keep a public reference, a schema name, flexible JSONB fields, confidence and review information, and the original extracted text and filename when available.

`log_record.user_id` references `users.id`. Owner-scoped queries are used by the dashboard, the source viewer, and conversation search. Signed-in graph checkpoints live in a separate SQLite file under `backend/data` by default. Guest graph checkpoints are kept in memory.

PostgreSQL stores normalized terms and alphanumeric prefixes in generated columns and indexes them with GIN. Exact search uses the stored terms. Related mode also checks prefixes and the bundled English synonym dictionary. Search pages are sorted newest first and use a creation timestamp and record ID as the cursor.

Run `alembic upgrade head` from `backend` before upgrading an Alembic-managed deployment. The prefix migration builds a stored column and index for existing records. Check runtime and available disk space on a restored copy before upgrading a large database. Keep backups and database dumps outside source control.
