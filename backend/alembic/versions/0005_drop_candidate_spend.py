"""drop candidate spend/workspace columns (spend feature removed)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-25

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: str | Sequence[str] | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('candidate', 'spend_updated_at')
    op.drop_column('candidate', 'usd_spend_cents')
    op.drop_column('candidate', 'workspace_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('candidate', sa.Column('workspace_id', sa.String(length=64), nullable=True))
    op.add_column('candidate', sa.Column('usd_spend_cents', sa.BigInteger(), nullable=True))
    op.add_column('candidate', sa.Column('spend_updated_at', sa.DateTime(timezone=True), nullable=True))
