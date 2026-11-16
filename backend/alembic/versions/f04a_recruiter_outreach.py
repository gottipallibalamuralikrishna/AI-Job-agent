"""Persistent per-user mail connection and recruiter outreach queue."""
from alembic import op

revision = 'f04a_recruiter_outreach'
down_revision = 'e93a_job_applications'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE outreach_accounts (
        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        email VARCHAR(320) NOT NULL, secret_ciphertext TEXT, paused_until TIMESTAMPTZ,
        connected_at TIMESTAMPTZ)''')
    op.execute('''CREATE TABLE outreach_campaigns (
        id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        request_key UUID NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL,
        sender_email VARCHAR(320) NOT NULL, sender_name TEXT NOT NULL,
        resume_path TEXT, resume_name TEXT, resume_sha256 VARCHAR(64),
        cancelled BOOLEAN NOT NULL DEFAULT false,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(user_id, request_key))''')
    op.execute('''CREATE TABLE outreach_messages (
        id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        campaign_id UUID NOT NULL REFERENCES outreach_campaigns(id) ON DELETE CASCADE,
        email VARCHAR(320) NOT NULL, recruiter_name TEXT, company TEXT,
        fingerprint VARCHAR(64) NOT NULL, rendered_subject TEXT NOT NULL, rendered_body TEXT NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'queued',
        error TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        started_at TIMESTAMPTZ, sent_at TIMESTAMPTZ,
        CHECK(status IN ('queued','sending','sent','failed','unknown','cancelled')),
        UNIQUE(user_id, fingerprint))''')
    op.execute('CREATE INDEX ix_outreach_messages_queue ON outreach_messages(status, created_at)')


def downgrade():
    op.drop_table('outreach_messages')
    op.drop_table('outreach_campaigns')
    op.drop_table('outreach_accounts')
