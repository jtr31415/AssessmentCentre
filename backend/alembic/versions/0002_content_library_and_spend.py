"""content library table + candidate spend/workspace columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-25

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: str | Sequence[str] | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'content_file',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_key', sa.String(length=64), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=255), nullable=False),
        sa.Column('media_type', sa.String(length=128), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_content_file_file_key'), 'content_file', ['file_key'], unique=True)

    op.add_column('candidate', sa.Column('workspace_id', sa.String(length=64), nullable=True))
    op.add_column('candidate', sa.Column('usd_spend_cents', sa.BigInteger(), nullable=True))
    op.add_column('candidate', sa.Column('spend_updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('candidate', 'spend_updated_at')
    op.drop_column('candidate', 'usd_spend_cents')
    op.drop_column('candidate', 'workspace_id')
    op.drop_index(op.f('ix_content_file_file_key'), table_name='content_file')
    op.drop_table('content_file')
