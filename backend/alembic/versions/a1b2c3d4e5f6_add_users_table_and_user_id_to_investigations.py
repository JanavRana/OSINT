"""add_users_table_and_user_id_to_investigations

Revision ID: a1b2c3d4e5f6
Revises: 708401118290
Create Date: 2026-08-06 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '708401118290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table and add user_id FK to investigations.
    
    This migration is idempotent - checks for existence before creating/adding.
    Safe for databases partially initialized with Base.metadata.create_all().
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # 1. Create users table only if it doesn't exist
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('email', sa.String(length=320), nullable=False),
            sa.Column('full_name', sa.String(length=255), nullable=False, server_default=''),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('otp_code', sa.String(length=6), nullable=True),
            sa.Column('otp_expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Add user_id column to investigations only if it doesn't exist
    investigations_columns = [col['name'] for col in inspector.get_columns('investigations')]
    if 'user_id' not in investigations_columns:
        op.add_column(
            'investigations',
            sa.Column('user_id', sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            'fk_investigations_user_id_users',
            'investigations', 'users',
            ['user_id'], ['id'],
            ondelete='SET NULL',
        )
        op.create_index(
            op.f('ix_investigations_user_id'), 'investigations', ['user_id'], unique=False
        )


def downgrade() -> None:
    """Remove user_id from investigations and drop users table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Remove user_id column if it exists
    investigations_columns = [col['name'] for col in inspector.get_columns('investigations')]
    if 'user_id' in investigations_columns:
        op.drop_index(op.f('ix_investigations_user_id'), table_name='investigations')
        op.drop_constraint('fk_investigations_user_id_users', 'investigations', type_='foreignkey')
        op.drop_column('investigations', 'user_id')
    
    # Drop users table if it exists
    if 'users' in inspector.get_table_names():
        op.drop_index(op.f('ix_users_email'), table_name='users')
        op.drop_table('users')
