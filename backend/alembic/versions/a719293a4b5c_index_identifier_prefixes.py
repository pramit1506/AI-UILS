"""Index alphanumeric prefixes for saved-record search."""
from alembic import op

from app.database.identifier_prefixes import install_identifier_prefixes
from app.database.workspace_v2 import install_workspace_v2

revision = "a719293a4b5c"
down_revision = "f60718293a4b"
branch_labels = None
depends_on = None


def upgrade():
    install_identifier_prefixes(op.get_bind())


def downgrade():
    install_workspace_v2(op.get_bind())
    op.drop_index("ix_log_record_search_prefixes", table_name="log_record")
    op.drop_column("log_record", "search_prefixes")
    op.execute("DROP FUNCTION uils_prefixes_v3(text[])")
