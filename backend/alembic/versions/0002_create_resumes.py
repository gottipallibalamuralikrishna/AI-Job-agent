
"""create resumes table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_create_resumes"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "resumes",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),

        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),

        sa.Column(
            "parsing_status",
            sa.String(20),
            nullable=False,
            server_default="uploaded",
        ),

        sa.Column("extracted_text", sa.Text(), nullable=True),

        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.UniqueConstraint(
            "stored_filename",
            name="uq_resumes_stored_filename",
        ),

        sa.CheckConstraint(
            "parsing_status IN ('uploaded', 'processing', 'parsed', 'failed')",
            name="ck_resumes_parsing_status",
        ),
    )

    op.create_index(
        "ix_resumes_user_id",
        "resumes",
        ["user_id"],
    )


def downgrade():
    op.drop_index("ix_resumes_user_id", table_name="resumes")
    op.drop_table("resumes")
