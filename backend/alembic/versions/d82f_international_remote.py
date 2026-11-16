"""Support opt-in international remote jobs and applicant location requirements."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d82f_international_remote"
down_revision = "c71e_unique_job_hash"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("include_international_remote", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("jobs", sa.Column("remote_eligible_locations", postgresql.JSONB(), nullable=False, server_default="[]"))


def downgrade():
    op.drop_column("jobs", "remote_eligible_locations")
    op.drop_column("users", "include_international_remote")
