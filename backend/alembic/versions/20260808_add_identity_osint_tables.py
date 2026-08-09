"""add identity osint tables

Revision ID: 20260808_identity
Revises: a1b2c3d4e5f6
Create Date: 2026-08-08

Adds tables for identity OSINT subsystem:
- scans: scan lifecycle and status
- scan_tasks: per-plugin task execution
- plugin_metrics_rollup: historical success metrics
- circuit_breaker_state: fault isolation state

Note: Reuses existing normalized_facts table with new fact_types for username results.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20260808_identity'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Scans table
    op.create_table(
        'scans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('investigation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('identifier_type', sa.String(50), nullable=False),
        sa.Column('identifier_value', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('options', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_scans_investigation_id', 'scans', ['investigation_id'])
    op.create_index('ix_scans_status', 'scans', ['status'])
    op.create_index('ix_scans_identifier_type', 'scans', ['identifier_type'])
    
    # Scan tasks table
    op.create_table(
        'scan_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plugin_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('raw_result_ref', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_scan_tasks_scan_id', 'scan_tasks', ['scan_id'])
    op.create_index('ix_scan_tasks_plugin_id', 'scan_tasks', ['plugin_id'])
    op.create_index('ix_scan_tasks_status', 'scan_tasks', ['status'])
    
    # Plugin metrics rollup table
    op.create_table(
        'plugin_metrics_rollup',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plugin_id', sa.String(100), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    op.create_index('ix_plugin_metrics_plugin_id', 'plugin_metrics_rollup', ['plugin_id'])
    op.create_index('ix_plugin_metrics_window', 'plugin_metrics_rollup', ['window_start', 'window_end'])
    
    # Circuit breaker state table
    op.create_table(
        'circuit_breaker_state',
        sa.Column('plugin_id', sa.String(100), primary_key=True),
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_probe_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('circuit_breaker_state')
    op.drop_table('plugin_metrics_rollup')
    op.drop_table('scan_tasks')
    op.drop_table('scans')
