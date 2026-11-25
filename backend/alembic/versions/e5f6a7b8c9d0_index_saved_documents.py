"""Retain source text and index document keywords, including existing records."""
from alembic import op
from app.database.search_v1 import install_search_v1

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    install_search_v1(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_log_record_owner_created_id", table_name="log_record")
    op.drop_index("ix_log_record_search_terms", table_name="log_record")
    op.drop_column("log_record", "search_terms")
    op.drop_column("log_record", "source_text")
    op.drop_column("log_record", "source_filename")
    op.execute("DROP FUNCTION uils_search_terms_v1(text)")
    op.execute("DROP FUNCTION uils_json_text_v1(jsonb)")
