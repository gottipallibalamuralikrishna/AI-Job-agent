"""Durable collection queue, primary resume, and independent contact retention."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "91c0_daily_collection"
down_revision = "2c1844205f00"
branch_labels = None
depends_on = None


def upgrade():
    # Normalize legacy selections before enforcing one primary per user.
    op.execute("""UPDATE resumes SET is_primary = false WHERE id IN (
        SELECT id FROM (SELECT id, row_number() OVER
        (PARTITION BY user_id ORDER BY created_at DESC, id) AS n
        FROM resumes WHERE is_primary) ranked WHERE n > 1)""")
    op.create_index("uq_resumes_primary_user", "resumes", ["user_id"], unique=True,
                    postgresql_where=sa.text("is_primary"))
    op.execute("""UPDATE resumes SET is_primary = true WHERE id IN (
        SELECT DISTINCT ON (r.user_id) r.id FROM resumes r
        LEFT JOIN resume_profiles p ON p.resume_id = r.id
        WHERE NOT EXISTS (SELECT 1 FROM resumes chosen WHERE chosen.user_id = r.user_id AND chosen.is_primary)
        ORDER BY r.user_id, (p.id IS NOT NULL AND r.parsing_status = 'parsed') DESC, r.created_at DESC, r.id)""")
    op.add_column("job_contacts", sa.Column("job_snapshot", postgresql.JSONB(), nullable=False, server_default="{}"))
    op.add_column("job_contacts", sa.Column("source_type", sa.String(30), nullable=True))
    op.execute("""UPDATE job_contacts c SET job_snapshot = jsonb_build_object(
        'id', j.id, 'title', j.title, 'company_name', j.company_name,
        'location', j.location, 'application_url', j.application_url, 'source_id', j.source_id,
        'collection_key', j.source_id::text || ':' || coalesce(j.external_id, j.title)),
        source_type = s.source_type FROM jobs j LEFT JOIN job_sources s ON s.id = j.source_id
        WHERE c.job_id = j.id""")
    # The previous migration let PostgreSQL assign the FK name.
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys("job_contacts"):
        if fk["constrained_columns"] == ["job_id"]:
            op.drop_constraint(fk["name"], "job_contacts", type_="foreignkey")
    op.alter_column("job_contacts", "job_id", nullable=True)
    op.create_foreign_key("fk_contacts_job_retained", "job_contacts", "jobs", ["job_id"], ["id"], ondelete="SET NULL")
    op.create_table("collection_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.UUID(), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_key", sa.String(200), unique=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("results", postgresql.JSONB(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Retained orphan contacts cannot be represented by the old schema.
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM job_contacts WHERE job_id IS NULL")):
        raise RuntimeError("Cannot downgrade while retained contacts have no job")
    op.drop_table("collection_runs")
    op.drop_constraint("fk_contacts_job_retained", "job_contacts", type_="foreignkey")
    op.alter_column("job_contacts", "job_id", nullable=False)
    op.create_foreign_key("job_contacts_job_id_fkey", "job_contacts", "jobs", ["job_id"], ["id"], ondelete="CASCADE")
    op.drop_column("job_contacts", "source_type")
    op.drop_column("job_contacts", "job_snapshot")
    op.drop_index("uq_resumes_primary_user", table_name="resumes")
