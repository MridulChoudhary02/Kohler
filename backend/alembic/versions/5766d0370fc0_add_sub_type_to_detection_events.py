"""add sub_type to detection_events

Revision ID: 5766d0370fc0
Revises: 0005_ticket_started_at
Create Date: 2026-09-20 12:51:14.733983

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5766d0370fc0'
down_revision: Union[str, None] = '0005_ticket_started_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('detection_events', sa.Column('sub_type', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('detection_events', 'sub_type')
