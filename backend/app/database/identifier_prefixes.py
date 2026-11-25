from sqlalchemy import text

from app.database.search_v1 import SEARCH_EXPRESSION


INDEXED_PREFIX_LENGTH = 24
PREFIXES_DDL = f"""
CREATE OR REPLACE FUNCTION uils_prefixes_v3(words text[])
RETURNS text[] LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
  SELECT array_agg(DISTINCT left(word, n))
  FROM unnest(words) AS w(word)
  CROSS JOIN LATERAL generate_series(3, least(length(word)-1, {INDEXED_PREFIX_LENGTH})) AS lengths(n)
  WHERE word ~ '^[[:alnum:]]+$'
$$;
"""
PREFIX_EXPRESSION = f"uils_prefixes_v3({SEARCH_EXPRESSION})"


def install_identifier_prefixes(connection):
    connection.execute(text(PREFIXES_DDL))
    connection.execute(text(
        "ALTER TABLE log_record ADD COLUMN IF NOT EXISTS search_prefixes text[] "
        f"GENERATED ALWAYS AS ({PREFIX_EXPRESSION}) STORED"
    ))
    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_log_record_search_prefixes ON log_record
        USING gin (search_prefixes)
    """))
    connection.execute(text("DROP INDEX IF EXISTS ix_log_record_prefixes_v2"))
