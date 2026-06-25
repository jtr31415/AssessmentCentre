"""candidate NDA acceptance timestamps

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: str | Sequence[str] | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('candidate', sa.Column('nda_accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('candidate', sa.Column('nda_declined_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('candidate', 'nda_declined_at')
    op.drop_column('candidate', 'nda_accepted_at')
