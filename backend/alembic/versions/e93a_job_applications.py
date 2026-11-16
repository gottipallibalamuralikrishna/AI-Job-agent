"""Keep user application history independently of collected job retention."""
from alembic import op
revision = "e93a_job_applications"
down_revision = "d82f_international_remote"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TABLE job_applications (user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, job_id UUID NOT NULL, snapshot JSONB NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY (user_id, job_id))")

def downgrade():
    op.drop_table("job_applications")
