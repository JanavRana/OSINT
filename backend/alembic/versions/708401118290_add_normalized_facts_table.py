"""add_normalized_facts_table

Revision ID: 708401118290
Revises: 
Create Date: 2026-07-12 23:24:18.959911

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '708401118290'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    This migration is idempotent - checks for table existence before creating.
    Safe for databases partially initialized with Base.metadata.create_all().
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Only create normalized_facts if it doesn't already exist
    if 'normalized_facts' not in existing_tables:
        op.create_table(
            'normalized_facts',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('investigation_id', sa.UUID(), nullable=False),
            sa.Column('connector_name', sa.String(length=255), nullable=False),
            sa.Column('fact_type', sa.String(length=255), nullable=False),
            sa.Column('value', sa.String(length=1000), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=False),
            sa.Column('metadata', sa.JSON(), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_normalized_facts_investigation_id'), 'normalized_facts', ['investigation_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'normalized_facts' in inspector.get_table_names():
        op.drop_index(op.f('ix_normalized_facts_investigation_id'), table_name='normalized_facts')
        op.drop_table('normalized_facts')
