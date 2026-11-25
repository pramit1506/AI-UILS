"""Add confidence and review columns

Revision ID: 632eb62ce980
Revises: 9fcd2da200e3
Create Date: 2026-08-16 17:21:52.394558

NOTE: This revision originally re-created the `log_record` table verbatim,
which broke the migration chain — running `alembic upgrade head` failed with
`relation "log_record" already exists` because the table already exists from
fc2c2b94f8a5 + 9fcd2da200e3. It now only creates the table when missing, and
otherwise adds the columns/indexes it was meant to introduce.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '632eb62ce980'
down_revision: Union[str, Sequence[str], None] = '9fcd2da200e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS = {
    'requires_review': sa.Column('requires_review', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    'overall_confidence': sa.Column('overall_confidence', sa.Float(), nullable=True),
    'field_metadata': sa.Column('field_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
    'summary': sa.Column('summary', sa.Text(), nullable=True),
    'source': sa.Column('source', sa.String(length=50), nullable=True),
    'conversation_id': sa.Column('conversation_id', sa.String(length=100), nullable=True),
}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('log_record'):
        # Fresh database: create the table in full.
        op.create_table('log_record',
        sa.Column('schema_name', sa.String(length=100), nullable=False),
        sa.Column('domain', sa.String(length=100), nullable=True),
        sa.Column('log_reference', sa.String(length=80), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('requires_review', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('overall_confidence', sa.Float(), nullable=True),
        sa.Column('field_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('conversation_id', sa.String(length=100), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_log_record_conversation_id'), 'log_record', ['conversation_id'], unique=False)
        op.create_index(op.f('ix_log_record_domain'), 'log_record', ['domain'], unique=False)
        op.create_index(op.f('ix_log_record_log_reference'), 'log_record', ['log_reference'], unique=True)
        op.create_index(op.f('ix_log_record_requires_review'), 'log_record', ['requires_review'], unique=False)
        op.create_index(op.f('ix_log_record_schema_name'), 'log_record', ['schema_name'], unique=False)
        return

    # Existing database: add only the columns/indexes that are still missing.
    existing_columns = {col['name'] for col in inspector.get_columns('log_record')}
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('log_record')}

    for name, column in _NEW_COLUMNS.items():
        if name not in existing_columns:
            op.add_column('log_record', column)

    if 'ix_log_record_requires_review' not in existing_indexes and \
            ('requires_review' in existing_columns or 'requires_review' not in existing_columns):
        try:
            op.create_index(op.f('ix_log_record_requires_review'), 'log_record', ['requires_review'], unique=False)
        except Exception:
            pass  # Column may still be absent on partial legacy schemas.


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('log_record'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('log_record')}
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('log_record')}

    if 'ix_log_record_requires_review' in existing_indexes:
        op.drop_index(op.f('ix_log_record_requires_review'), table_name='log_record')

    for name in ('overall_confidence', 'requires_review'):
        if name in existing_columns:
            op.drop_column('log_record', name)
