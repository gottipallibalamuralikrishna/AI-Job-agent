"""Reusable user-owned recruiter email templates."""
from alembic import op

revision = 'g15b_email_templates'
down_revision = 'f04a_recruiter_outreach'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE outreach_templates (
        id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL, subject VARCHAR(200) NOT NULL, body TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())''')
    op.execute('CREATE INDEX ix_outreach_templates_user ON outreach_templates(user_id)')
    op.execute('ALTER TABLE outreach_campaigns ADD COLUMN template_id UUID REFERENCES outreach_templates(id) ON DELETE SET NULL')
    op.execute('ALTER TABLE outreach_campaigns ADD COLUMN template_name VARCHAR(100)')


def downgrade():
    op.drop_column('outreach_campaigns', 'template_name')
    op.drop_column('outreach_campaigns', 'template_id')
    op.drop_table('outreach_templates')
