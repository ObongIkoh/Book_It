"""add revoked_tokens table

Revision ID: 140052189d1a
Revises: f63dbe8ded0d
Create Date: 2025-09-27 20:32:06.102791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '140052189d1a'
down_revision: Union[str, None] = 'f63dbe8ded0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("jti", sa.String, unique=True, nullable=False),  # JWT ID
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("revoked_tokens")