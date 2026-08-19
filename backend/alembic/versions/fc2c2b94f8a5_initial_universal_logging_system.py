"""initial_universal_logging_system

Revision ID: fc2c2b94f8a5
Revises: 
Create Date: 2026-08-01 12:00:00.000000

Creates the universal log_record table with a JSONB data column.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fc2c2b94f8a5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Drop legacy tables (safe — auto-drop on fresh systems too)       #
    # ------------------------------------------------------------------ #
    op.execute("DROP TABLE IF EXISTS complaint CASCADE")
    op.execute("DROP TABLE IF EXISTS customer CASCADE")

    # Also drop any old Alembic version stamps for those migrations
    op.execute("""
        DELETE FROM alembic_version
        WHERE version_num IN ('209318d5b937', 'b8b1f3fb1d12')
    """)

    # ------------------------------------------------------------------ #
    # 2. Create universal log_record table                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        'log_record',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('schema_name', sa.String(100), nullable=False, index=True),
        sa.Column('domain', sa.String(100), nullable=True, index=True),
        sa.Column('log_reference', sa.String(80), nullable=False, unique=True, index=True),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('field_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('conversation_id', sa.String(100), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )

    # GIN index on JSONB data column for fast full-text JSONB searches
    op.create_index(
        'ix_log_record_data_gin',
        'log_record',
        ['data'],
        postgresql_using='gin',
    )


def downgrade() -> None:
    op.drop_index('ix_log_record_data_gin', table_name='log_record')
    op.drop_table('log_record')
