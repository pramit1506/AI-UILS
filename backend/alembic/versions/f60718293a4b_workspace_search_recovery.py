"""Index partial words and support one-time account recovery codes."""
from alembic import op
from app.database.workspace_v2 import install_workspace_v2

revision = "f60718293a4b"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    install_workspace_v2(op.get_bind())


def downgrade():
    op.drop_index("ix_log_record_prefixes_v2", table_name="log_record")
    op.execute("DROP FUNCTION uils_prefixes_v2(text[])")
    for column in ("recovery_attempts", "recovery_expires", "recovery_digest", "session_version"):
        op.drop_column("users", column)
