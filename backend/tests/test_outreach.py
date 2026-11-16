import uuid
import hashlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.endpoints.outreach import Message, cancel
from app.models.job_contact import JobContact
from app.models.resume import Resume
from app.services import outreach_service as service
from tests.test_collection_flow import db, seed_profile


@pytest.fixture
def setup(db, monkeypatch, tmp_path):
    user, resume, _ = seed_profile(db)
    monkeypatch.setattr(service.settings, 'secret_key', 'test-outreach-encryption-key-with-32-characters')
    monkeypatch.setattr(service.settings, 'resume_storage_dir', str(tmp_path / 'resumes'))
    monkeypatch.setattr(service, 'STORAGE', tmp_path / 'snapshots')
    path = tmp_path / 'resumes' / 'resume.pdf'
    path.parent.mkdir()
    path.write_bytes(b'%PDF-test-resume')
    resume.storage_path = str(path)
    contacts = [JobContact(contact_type='email', contact_value=email, contact_name='Recruiter',
        source_type='spreadsheet', job_snapshot={'company_name': 'Example'})
        for email in ('first@example.com', 'second@example.com', 'first@example.com')]
    db.add_all(contacts)
    db.execute(text('INSERT INTO outreach_accounts(user_id,email,secret_ciphertext,connected_at) VALUES(:user,:email,:secret,now())'),
        {'user': user.id, 'email': 'sender@gmail.com', 'secret': service.cipher().encrypt(b'test-app-password').decode()})
    db.commit()
    monkeypatch.setattr(service, 'engine', db.get_bind())
    monkeypatch.setattr(service, 'SessionLocal', lambda: Session(db.get_bind()))
    monkeypatch.setattr(service, 'LOCK_ID', int.from_bytes(user.id.bytes[:8], signed=True))
    return user, resume, contacts, path


def request():
    return Message(all_imported=True, subject='Opportunities at {company}',
        body='Hello {recruiter_name},\nPlease review my experience.\n{sender_name}', request_key=uuid.uuid4())


def approved(db, user):
    message = request()
    from app.services.email_template_service import save_template, TemplateInput
    template = save_template(db, user, TemplateInput(name='Test outreach', subject=message.subject, body=message.body))
    message.template_id = template['id']
    message.preview_token = service.preview(db, user, message)['preview_token']
    return message


def fake_smtp(monkeypatch, fail=None):
    sent = []
    class SMTP:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def login(self, *args):
            return None
        def send_message(self, message):
            if fail:
                raise fail
            sent.append(message)
            return {}
    monkeypatch.setattr(service.smtplib, 'SMTP_SSL', SMTP)
    return sent


def test_preview_queue_and_repeat_click_are_deduplicated(db, setup):
    user, resume, contacts, _ = setup
    message = approved(db, user)
    preview = service.preview(db, user, message)
    assert preview['recipient_count'] == 2
    assert 'Example' in preview['subject']
    result = service.queue(db, user, message)
    assert result['queued'] == 2
    assert service.queue(db, user, message)['already_queued']
    message.request_key = uuid.uuid4()
    assert service.queue(db, user, message)['duplicates_skipped'] == 2
    assert db.execute(text('SELECT count(*) FROM outreach_messages')).scalar() == 2


def test_changed_attachment_requires_another_preview(db, setup):
    user, _, _, path = setup
    message = approved(db, user)
    path.write_bytes(b'%PDF-changed')
    with pytest.raises(HTTPException) as exc:
        service.queue(db, user, message)
    assert exc.value.status_code == 409


def test_worker_sends_one_private_email_with_frozen_resume_and_daily_cap(db, setup, monkeypatch):
    user, _, _, path = setup
    service.queue(db, user, approved(db, user))
    path.unlink()
    monkeypatch.setattr(service.settings, 'outreach_daily_limit', 1)
    sent = fake_smtp(monkeypatch)
    service.send_one()
    service.send_one()
    assert len(sent) == 1
    assert ',' not in sent[0]['To']
    assert 'Bcc' not in sent[0]
    assert list(sent[0].iter_attachments())[0].get_payload(decode=True) == b'%PDF-test-resume'
    db.expire_all()
    assert db.execute(text("SELECT count(*) FROM outreach_messages WHERE status='sent'")).scalar() == 1


def test_cancel_is_owner_scoped_and_stops_queued_mail(db, setup, monkeypatch):
    user, _, _, _ = setup
    result = service.queue(db, user, approved(db, user))
    other, _, _ = seed_profile(db)
    with pytest.raises(HTTPException):
        cancel(result['id'], db, other)
    db.rollback()
    cancel(result['id'], db, user)
    sent = fake_smtp(monkeypatch)
    service.send_one()
    assert not sent
    assert service.history(db, other) == []


def test_uncertain_delivery_is_not_automatically_retried(db, setup, monkeypatch):
    user, _, _, _ = setup
    service.queue(db, user, approved(db, user))
    fake_smtp(monkeypatch, fail=TimeoutError())
    service.send_one()
    db.execute(text("UPDATE outreach_messages SET status='cancelled' WHERE status='queued'"))
    db.commit()
    sent = fake_smtp(monkeypatch)
    service.send_one()
    assert not sent
    assert db.execute(text("SELECT count(*) FROM outreach_messages WHERE status='unknown'")).scalar() == 1


def test_connection_password_is_encrypted_and_never_returned(db, setup, monkeypatch):
    user, _, _, _ = setup
    fake_smtp(monkeypatch)
    service.connect_account(db, user, 'sender@gmail.com', 'secret-test-password')
    stored = db.execute(text('SELECT secret_ciphertext FROM outreach_accounts WHERE user_id=:user'), {'user': user.id}).scalar()
    assert 'secret-test-password' not in stored
    assert service.cipher().decrypt(stored.encode()).decode() == 'secret-test-password'
    assert 'secret_ciphertext' not in service.context(db, user)


def test_provider_quota_rejection_pauses_the_queue(db, setup, monkeypatch):
    user, _, _, _ = setup
    service.queue(db, user, approved(db, user))
    fake_smtp(monkeypatch, fail=service.smtplib.SMTPDataError(452, b'Sending quota exceeded'))
    service.send_one()
    assert db.execute(text('SELECT paused_until IS NOT NULL FROM outreach_accounts WHERE user_id=:user'), {'user': user.id}).scalar()
    sent = fake_smtp(monkeypatch)
    service.send_one()
    assert not sent
    assert db.execute(text("SELECT count(*) FROM outreach_messages WHERE status='queued'")).scalar() == 2


def test_server_key_change_pauses_instead_of_losing_the_queue(db, setup, monkeypatch):
    user, _, _, _ = setup
    service.queue(db, user, approved(db, user))
    monkeypatch.setattr(service.settings, 'outreach_encryption_key', service.Fernet.generate_key().decode())
    sent = fake_smtp(monkeypatch)
    service.send_one()
    assert not sent
    assert db.execute(text('SELECT connected_at FROM outreach_accounts WHERE user_id=:user'), {'user': user.id}).scalar() is None
    assert db.execute(text("SELECT count(*) FROM outreach_messages WHERE status='queued'")).scalar() == 2


def test_verified_legacy_resume_path_can_be_attached(db, setup, monkeypatch, tmp_path):
    user, resume, _, path = setup
    resume.stored_filename = path.name
    resume.checksum_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(service.settings, 'resume_storage_dir', str(tmp_path / 'new-resume-directory'))
    db.commit()
    assert service.preview(db, user, request())['resume_name'] == resume.original_filename
    path.write_bytes(b'changed')
    with pytest.raises(HTTPException):
        service.preview(db, user, request())
