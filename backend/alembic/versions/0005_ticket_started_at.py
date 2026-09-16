"""Add started_at to tickets

Revision ID: 0005_ticket_started_at
Revises: 0004_ticket_escalated_flag
Create Date: 2026-09-16 00:24:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_ticket_started_at"
down_revision = "0004_ticket_escalated_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "started_at")
