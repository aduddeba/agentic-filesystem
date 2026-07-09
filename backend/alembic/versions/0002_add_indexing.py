"""add indexing: pgvector extension, file metadata columns, chunks table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("files", sa.Column("mime_type", sa.String(), nullable=True))
    op.add_column("files", sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("files", sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("files", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("files", sa.Column("index_error", sa.String(), nullable=True))

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_id", sa.Integer(), sa.ForeignKey("files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chunks_file_id", "chunks", ["file_id"])


def downgrade() -> None:
    op.drop_index("ix_chunks_file_id", table_name="chunks")
    op.drop_table("chunks")

    op.drop_column("files", "index_error")
    op.drop_column("files", "indexed_at")
    op.drop_column("files", "char_count")
    op.drop_column("files", "word_count")
    op.drop_column("files", "mime_type")
