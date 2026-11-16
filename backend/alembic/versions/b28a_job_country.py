"""Persist each user's preferred job country."""
from alembic import op
import sqlalchemy as sa

revision = "b28a_job_country"
down_revision = "91c0_daily_collection"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("preferred_job_country", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("users", "preferred_job_country")
