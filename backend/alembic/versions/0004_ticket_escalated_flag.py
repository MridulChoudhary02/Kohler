"""Add is_escalated to tickets

Revision ID: 0004_ticket_escalated_flag
Revises: 0003_ticket_timestamps
Create Date: 2026-09-16 00:13:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_ticket_escalated_flag"
down_revision = "0003_ticket_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("is_escalated", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("tickets", "is_escalated")
