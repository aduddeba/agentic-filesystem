"""add memory tables: task_records, file_history_entries, preferences

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "file_history_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("task_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_file_history_entries_task_id", "file_history_entries", ["task_id"])
    op.create_index("ix_file_history_entries_path", "file_history_entries", ["path"])

    op.create_table(
        "preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
    )
    op.create_index("ix_preferences_key", "preferences", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_preferences_key", table_name="preferences")
    op.drop_table("preferences")

    op.drop_index("ix_file_history_entries_path", table_name="file_history_entries")
    op.drop_index("ix_file_history_entries_task_id", table_name="file_history_entries")
    op.drop_table("file_history_entries")

    op.drop_table("task_records")
