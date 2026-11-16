import json

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.services import email_template_service as templates
from app.services import outreach_service as service
from tests.test_collection_flow import db, seed_profile
from tests.test_outreach import setup, approved, request, fake_smtp


@pytest.mark.parametrize('filename,content', [
    ('Intro.txt', b'Subject: Opportunities at {company}\r\n\r\nHello {recruiter_name}, please review my resume.'),
    ('intro.json', json.dumps({'name': 'Intro', 'subject': 'Opportunities at {company}', 'body': 'Hello {recruiter_name}, please review my resume.'}).encode()),
], ids=['text', 'json'])
def test_uploaded_template_keeps_personalization(filename, content):
    template = templates.parse_upload(filename, content)
    assert template.name == 'Intro'
    assert template.subject == 'Opportunities at {company}'
    assert '{recruiter_name}' in template.body


@pytest.mark.parametrize('filename,content,status', [
    ('intro.pdf', b'hello', 415),
    ('intro.txt', b'x' * 131073, 413),
    ('intro.txt', b'No subject header', 422),
    ('intro.json', b'{broken', 422),
    ('intro.txt', b'\xff\xfe', 422),
    ('intro.json', json.dumps({'name': 'Intro', 'subject': 'Hi\nBcc: someone@example.com', 'body': 'Please review my resume.'}).encode(), 422),
], ids=['unsupported', 'oversize', 'missing-header', 'malformed-json', 'encoding', 'header-newline'])
def test_invalid_uploads_are_rejected(filename, content, status):
    with pytest.raises(HTTPException) as exc:
        templates.parse_upload(filename, content)
    assert exc.value.status_code == status


def test_templates_are_private_to_their_owner(db, setup):
    user, _, _, _ = setup
    other, _, _ = seed_profile(db)
    template = templates.save_template(db, user, templates.TemplateInput(name='Intro', subject='Frontend role', body='Please review my experience.'))
    assert templates.list_templates(db, other) == []
    with pytest.raises(HTTPException) as exc:
        templates.get_template(db, other, template['id'])
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException):
        templates.save_template(db, other, templates.TemplateInput(name='Stolen', subject='Changed', body='Please review my experience.'), template['id'])
    assert templates.get_template(db, user, template['id'])['name'] == 'Intro'


def test_send_requires_a_saved_template(db, setup):
    user, _, _, _ = setup
    message = request()
    message.preview_token = service.preview(db, user, message)['preview_token']
    with pytest.raises(HTTPException) as exc:
        service.queue(db, user, message)
    assert exc.value.status_code == 422


def test_updated_template_requires_a_fresh_selection_and_preview(db, setup):
    user, _, _, _ = setup
    message = approved(db, user)
    templates.save_template(db, user, templates.TemplateInput(name='Updated', subject='New subject', body=message.body), message.template_id)
    with pytest.raises(HTTPException) as exc:
        service.queue(db, user, message)
    assert exc.value.status_code == 409
    assert db.execute(text('SELECT count(*) FROM outreach_messages')).scalar() == 0


def test_queued_content_survives_template_updates_and_deletion(db, setup, monkeypatch):
    user, _, _, _ = setup
    message = approved(db, user)
    campaign = service.queue(db, user, message)
    templates.save_template(db, user, templates.TemplateInput(name='Updated', subject='Different subject', body='Different body for another campaign.'), message.template_id)
    db.execute(text('DELETE FROM outreach_templates WHERE id=:id'), {'id': message.template_id})
    db.commit()
    sent = fake_smtp(monkeypatch)
    service.send_one()
    assert len(sent) == 1
    assert sent[0]['Subject'] == 'Opportunities at Example'
    assert 'Please review my experience.' in sent[0].get_body().get_content()
    record = db.execute(text('SELECT template_id,template_name FROM outreach_campaigns WHERE id=:id'), {'id': campaign['id']}).mappings().one()
    assert record['template_id'] is None
    assert record['template_name'] == 'Test outreach'
