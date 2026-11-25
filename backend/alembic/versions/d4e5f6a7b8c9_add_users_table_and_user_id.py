"""add users table and log_record.user_id

Revision ID: d4e5f6a7b8c9
Revises: 632eb62ce980
Create Date: 2026-10-27 12:00:00.000000

Closes the gap in the migration chain: no previous revision created the
`users` table even though `log_record.user_id` is a foreign key to it (the
table only came into existence via `Base.metadata.create_all` at startup,
bypassing Alembic entirely).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = '632eb62ce980'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('username', sa.String(length=100), nullable=False),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('full_name', sa.String(length=150), nullable=True),
            sa.Column('role', sa.String(length=50), nullable=False, server_default='user'),
            sa.Column('avatar_url', sa.String(length=500), nullable=True),
            sa.Column('bio', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email'),
            sa.UniqueConstraint('username'),
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    if inspector.has_table('log_record'):
        existing_columns = {col['name'] for col in inspector.get_columns('log_record')}
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('log_record')}

        if 'user_id' not in existing_columns:
            op.add_column(
                'log_record',
                sa.Column('user_id', sa.Uuid(), nullable=True),
            )
            op.execute(
                "ALTER TABLE log_record "
                "ADD CONSTRAINT fk_log_record_user_id "
                "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL"
            )
        if 'ix_log_record_user_id' not in existing_indexes:
            op.create_index('ix_log_record_user_id', 'log_record', ['user_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('log_record'):
        pass
    else:
        existing_columns = {col['name'] for col in inspector.get_columns('log_record')}
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('log_record')}

        if 'ix_log_record_user_id' in existing_indexes:
            op.drop_index('ix_log_record_user_id', table_name='log_record')
        if 'user_id' in existing_columns:
            op.drop_column('log_record', 'user_id')

    if inspector.has_table('users'):
        op.drop_index(op.f('ix_users_username'), table_name='users')
        op.drop_index(op.f('ix_users_email'), table_name='users')
        op.drop_table('users')
