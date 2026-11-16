"""Enforce global job deduplication while preserving contacts and user matches."""
from alembic import op

revision = "c71e_unique_job_hash"
down_revision = "b28a_job_country"
branch_labels = None
depends_on = None


def upgrade():
    # Retain the first extraction date so deduplication does not extend retention.
    op.execute("""CREATE TEMP TABLE merged_jobs ON COMMIT DROP AS
        SELECT id, first_value(id) OVER (PARTITION BY job_hash ORDER BY created_at, id) AS keep_id
        FROM jobs WHERE job_hash IS NOT NULL""")
    op.execute("""DELETE FROM job_matches WHERE id IN (
        SELECT id FROM (SELECT m.id, row_number() OVER (
            PARTITION BY m.user_id, m.resume_id, coalesce(d.keep_id, m.job_id)
            ORDER BY m.updated_at DESC, m.id) AS n
            FROM job_matches m LEFT JOIN merged_jobs d ON d.id = m.job_id) ranked
        WHERE n > 1)""")
    op.execute("""UPDATE job_matches m SET job_id = d.keep_id FROM merged_jobs d
        WHERE m.job_id = d.id AND d.id <> d.keep_id""")
    # Reassign contacts where possible. Identical contacts retain their snapshots
    # as independent records rather than being lost to a uniqueness conflict.
    op.execute("""UPDATE job_contacts SET job_id = NULL WHERE id IN (
        SELECT id FROM (SELECT c.id, row_number() OVER (
            PARTITION BY d.keep_id, c.contact_type, c.contact_value
            ORDER BY (c.job_id = d.keep_id) DESC, c.created_at, c.id) AS n
            FROM job_contacts c JOIN merged_jobs d ON d.id = c.job_id) ranked
        WHERE n > 1)""")
    op.execute("""UPDATE job_contacts c SET job_id = d.keep_id FROM merged_jobs d
        WHERE c.job_id = d.id AND d.id <> d.keep_id""")
    op.execute("DELETE FROM jobs WHERE id IN (SELECT id FROM merged_jobs WHERE id <> keep_id)")
    op.drop_index("ix_jobs_job_hash", table_name="jobs")
    op.create_index("ix_jobs_job_hash", "jobs", ["job_hash"], unique=True)


def downgrade():
    op.drop_index("ix_jobs_job_hash", table_name="jobs")
    op.create_index("ix_jobs_job_hash", "jobs", ["job_hash"], unique=False)
