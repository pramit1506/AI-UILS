"""Versioned PostgreSQL objects shared by Alembic and the legacy startup bootstrap.

Keep v1 immutable. A tokenizer change requires a new revision and index rebuild.
"""

from sqlalchemy import text


# Count each keyword once per document. GIN can test containment over text[]
# without tsvector's 1 MB document limit. No searchable query can include a
# term longer than 256 characters; bounding terms also bounds GIN entry size.
TOKENIZER_DDL = """
CREATE OR REPLACE FUNCTION uils_search_terms_v1(input_text text)
RETURNS text[] LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
    SELECT array_agg(DISTINCT term)
    FROM string_to_table(
        regexp_replace(lower(normalize(input_text, NFC)), '[[:space:][:punct:][:cntrl:]]+', ' ', 'g'), ' '
    ) AS words(term)
    WHERE length(term) BETWEEN 1 AND 256
$$
"""

# Walk objects and arrays at any depth. Casting the JSON document to text
# would index its escape sequences (e.g. a newline followed by "Paid" as "nPaid").
JSON_TEXT_DDL = """
CREATE OR REPLACE FUNCTION uils_json_text_v1(input_data jsonb)
RETURNS text LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
    WITH RECURSIVE nodes(key, val) AS (
        SELECT NULL::text, input_data
        UNION ALL
        SELECT child.key, child.val
        FROM nodes
        CROSS JOIN LATERAL (
            SELECT key, value AS val
            FROM jsonb_each(CASE WHEN jsonb_typeof(nodes.val) = 'object' THEN nodes.val ELSE '{}' END)
            UNION ALL
            SELECT NULL, value
            FROM jsonb_array_elements(CASE WHEN jsonb_typeof(nodes.val) = 'array' THEN nodes.val ELSE '[]' END)
        ) AS child
    )
    SELECT string_agg(coalesce(key, '') || ' ' ||
        CASE WHEN jsonb_typeof(val) IN ('object', 'array') THEN ''
             WHEN jsonb_typeof(val) = 'null' THEN 'null'
             ELSE val #>> '{}' END, ' ')
    FROM nodes
$$
"""

SEARCH_EXPRESSION = """
uils_search_terms_v1(
    coalesce(log_reference, '') || ' ' || coalesce(schema_name, '') || ' ' ||
    coalesce(domain, '') || ' ' || coalesce(source, '') || ' ' ||
    coalesce(summary, '') || ' ' || coalesce(uils_json_text_v1(data), '') || ' ' ||
    coalesce(source_filename, '') || ' ' || coalesce(source_text, '')
)
"""


def install_search_v1(connection):
    """Upgrade populated databases including ones originally created by create_all."""
    connection.execute(text(TOKENIZER_DDL))
    connection.execute(text(JSON_TEXT_DDL))
    connection.execute(text("ALTER TABLE log_record ADD COLUMN IF NOT EXISTS source_filename text"))
    connection.execute(text("ALTER TABLE log_record ADD COLUMN IF NOT EXISTS source_text text"))
    connection.execute(text(
        f"ALTER TABLE log_record ADD COLUMN IF NOT EXISTS search_terms text[] "
        f"GENERATED ALWAYS AS ({SEARCH_EXPRESSION}) STORED"
    ))
    connection.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_log_record_search_terms ON log_record USING gin(search_terms)"
    ))
    connection.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_log_record_owner_created_id ON log_record(user_id, created_at, id)"
    ))
