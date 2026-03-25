"""add webhook columns to runs

Revision ID: 180f15f2fefb
Revises: b8e51bb17c31
Create Date: 2026-03-25 11:31:48.453128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '180f15f2fefb'
down_revision: Union[str, Sequence[str], None] = 'b8e51bb17c31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add webhook_url and webhook_events columns to runs table."""
    with op.batch_alter_table("runs") as batch_op:
        batch_op.add_column(sa.Column("webhook_url", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("webhook_events", sa.Text, nullable=True))


def downgrade() -> None:
    """Remove webhook columns from runs table."""
    with op.batch_alter_table("runs") as batch_op:
        batch_op.drop_column("webhook_events")
        batch_op.drop_column("webhook_url")
