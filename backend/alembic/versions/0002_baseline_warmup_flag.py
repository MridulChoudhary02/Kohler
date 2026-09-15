"""Add warmup_complete and warmup_started_at to baseline_profiles

Implements the PRD Section 7.5 warm-up state as an explicit, queryable
flag rather than relying on timestamp arithmetic at runtime.

  warmup_complete    BOOLEAN NOT NULL DEFAULT FALSE
  warmup_started_at  TIMESTAMPTZ

Revision ID: 0002_baseline_warmup_flag
Revises: 0001_initial_schema
Create Date: 2026-09-15 14:16:00
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0002_baseline_warmup_flag"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "baseline_profiles",
        sa.Column("warmup_complete", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "baseline_profiles",
        sa.Column("warmup_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("baseline_profiles", "warmup_started_at")
    op.drop_column("baseline_profiles", "warmup_complete")
