"""add log_reference

Revision ID: 9fcd2da200e3
Revises: fc2c2b94f8a5
Create Date: 2026-08-07 12:51:19.768502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9fcd2da200e3'
down_revision: Union[str, Sequence[str], None] = 'fc2c2b94f8a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Guarded: adding a NOT NULL column without a server default fails on any
    # table that already contains rows. Also idempotent — re-running the chain
    # on a database provisioned by Base.metadata.create_all used to crash here.
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('log_record'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('log_record')}
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('log_record')}

    if 'schema_name' in existing_columns:
        op.alter_column('log_record', 'schema_name',
                   existing_type=sa.VARCHAR(length=100),
                   nullable=False)
    if 'data' in existing_columns:
        op.alter_column('log_record', 'data',
                   existing_type=postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False)
    if 'field_metadata' in existing_columns:
        op.alter_column('log_record', 'field_metadata',
                   existing_type=postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False)

    if 'log_reference' not in existing_columns:
        op.add_column('log_record', sa.Column('log_reference', sa.String(length=80), nullable=True))
        # Backfill existing rows so the NOT NULL conversion below succeeds.
        op.execute("UPDATE log_record SET log_reference = 'LOG-' || upper(substring(gen_random_uuid()::text, 1, 8)) WHERE log_reference IS NULL")
        op.alter_column('log_record', 'log_reference',
                   existing_type=sa.String(length=80),
                   nullable=False)
    if 'summary' not in existing_columns:
        op.add_column('log_record', sa.Column('summary', sa.Text(), nullable=True))
    if 'source' not in existing_columns:
        op.add_column('log_record', sa.Column('source', sa.String(length=50), nullable=True))
    if 'conversation_id' not in existing_columns:
        op.add_column('log_record', sa.Column('conversation_id', sa.String(length=100), nullable=True))

    if 'ix_log_record_conversation_id' not in existing_indexes:
        op.create_index(op.f('ix_log_record_conversation_id'), 'log_record', ['conversation_id'], unique=False)
    if 'ix_log_record_log_reference' not in existing_indexes:
        op.create_index(op.f('ix_log_record_log_reference'), 'log_record', ['log_reference'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('log_record'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('log_record')}
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('log_record')}

    if 'ix_log_record_log_reference' in existing_indexes:
        op.drop_index(op.f('ix_log_record_log_reference'), table_name='log_record')
    if 'ix_log_record_conversation_id' in existing_indexes:
        op.drop_index(op.f('ix_log_record_conversation_id'), table_name='log_record')
    op.alter_column('log_record', 'field_metadata',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=True)
    op.alter_column('log_record', 'data',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=True)
    op.alter_column('log_record', 'schema_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
    for column in ('conversation_id', 'source', 'summary', 'log_reference'):
        if column in existing_columns:
            op.drop_column('log_record', column)
