
"""create resume profiles table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_create_resume_profiles"
down_revision = "0002_create_resumes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "resume_profiles",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "resume_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),

        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),

        sa.Column(
            "profile_data",
            postgresql.JSONB(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_resume_profiles_user_id",
        "resume_profiles",
        ["user_id"],
    )


def downgrade():
    op.drop_index(
        "ix_resume_profiles_user_id",
        table_name="resume_profiles",
    )

    op.drop_table("resume_profiles")
