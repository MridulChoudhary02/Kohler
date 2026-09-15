"""Add acknowledged_at and resolved_at to tickets

Revision ID: 0003_ticket_timestamps
Revises: 0002_baseline_warmup_flag
Create Date: 2026-09-16 00:08:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_ticket_timestamps"
down_revision = "0002_baseline_warmup_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "resolved_at")
    op.drop_column("tickets", "acknowledged_at")
