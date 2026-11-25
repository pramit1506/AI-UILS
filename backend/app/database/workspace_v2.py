from sqlalchemy import text


def install_workspace_v2(connection, *, legacy_index=True):
    connection.execute(text("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS session_version integer NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS recovery_digest varchar(64),
        ADD COLUMN IF NOT EXISTS recovery_expires timestamptz,
        ADD COLUMN IF NOT EXISTS recovery_attempts integer NOT NULL DEFAULT 0
    """))
    if not legacy_index:
        return
    connection.execute(text("""
        CREATE OR REPLACE FUNCTION uils_prefixes_v2(words text[])
        RETURNS text[] LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
          SELECT array_agg(DISTINCT left(word, n))
          FROM unnest(words) AS w(word)
          CROSS JOIN LATERAL generate_series(3, least(length(word)-1, 10)) AS lengths(n)
          WHERE word ~ '^[[:alpha:]]+$'
        $$
    """))
    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_log_record_prefixes_v2 ON log_record
        USING gin (uils_prefixes_v2(search_terms))
    """))
