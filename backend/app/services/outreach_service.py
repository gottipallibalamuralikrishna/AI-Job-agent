"""Explicitly queued recruiter email, independent of the Codex Gmail connection."""
import hashlib
import hmac
import json
import logging
import mimetypes
import os
import smtplib
import ssl
import time
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.models.job_contact import JobContact
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.models.user import User

logger = logging.getLogger(__name__)
LOCK_ID = 82614082
STORAGE = Path(__file__).resolve().parents[2] / 'private_storage/outreach'
EMAIL = TypeAdapter(EmailStr)


def cipher():
    try:
        if settings.outreach_encryption_key:
            return Fernet(settings.outreach_encryption_key.encode())
        STORAGE.mkdir(parents=True, exist_ok=True)
        key_path = STORAGE / '.mail-key'
        if not key_path.exists():
            try:
                descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(Fernet.generate_key())
        for _ in range(10):
            key = key_path.read_bytes()
            if len(key) >= 44:
                return Fernet(key)
            time.sleep(0.02)
    except (OSError, ValueError):
        pass
    raise HTTPException(503, 'Mail encryption storage is unavailable. Check the server configuration.')


def connect_account(db, user, email, app_password):
    password = app_password.replace(' ', '')
    if not email.lower().endswith('@gmail.com'):
        raise HTTPException(422, 'This connection currently supports personal Gmail accounts.')
    encrypted = cipher().encrypt(password.encode()).decode()
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ssl.create_default_context(), timeout=20) as smtp:
            smtp.login(email, password)
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(422, 'Gmail rejected the app password. Check the address and Google app password.')
    except (OSError, smtplib.SMTPException):
        raise HTTPException(502, 'Unable to connect to Gmail. Please retry later.')
    db.execute(text('''INSERT INTO outreach_accounts (user_id,email,secret_ciphertext,connected_at)
        VALUES (:user,:email,:secret,now()) ON CONFLICT(user_id) DO UPDATE
        SET email=:email, secret_ciphertext=:secret, connected_at=now(), paused_until=NULL'''),
        {'user': user.id, 'email': email, 'secret': encrypted})
    db.commit()


def recipients(db, all_imported, contact_ids, manual_emails=()):
    query = db.query(JobContact).filter_by(contact_type='email')
    if all_imported:
        query = query.filter_by(source_type='spreadsheet')
    else:
        query = query.filter(JobContact.id.in_(contact_ids))
    found = {}
    for contact in query.order_by(JobContact.created_at):
        try:
            email = str(EMAIL.validate_python(contact.contact_value)).lower()
        except ValueError:
            continue
        found.setdefault(email, {'email': email, 'recruiter_name': contact.contact_name or 'Recruiter',
            'company': (contact.job.company_name if contact.job else (contact.job_snapshot or {}).get('company_name')) or 'your organisation'})
    for value in manual_emails:
        email = str(EMAIL.validate_python(value)).lower()
        found.setdefault(email, {'email': email, 'recruiter_name': 'Recruiter', 'company': 'your organisation'})
    return list(found.values())


def context(db, user):
    account = db.execute(text('SELECT email,connected_at FROM outreach_accounts WHERE user_id=:user'), {'user': user.id}).mappings().first()
    resume = db.query(Resume).filter_by(user_id=user.id, is_primary=True).first()
    profile = db.query(ResumeProfile).filter_by(resume_id=resume.id).first() if resume else None
    data = profile.profile_data if profile else {}
    role = data.get('professional_title') or 'Software Developer'
    skills = ', '.join((data.get('technical_skills') or [])[:6])
    experience = data.get('total_experience_years')
    intro = f'I have {experience} years of experience' if experience is not None else 'My experience includes software development'
    body = (f'Hello {{recruiter_name}},\n\nI am interested in {role} opportunities at {{company}}. '
            f'{intro}' + (f', with skills in {skills}.' if skills else '.') +
            '\n\nPlease let me know if you have a suitable opening. I would be happy to discuss my experience.\n\nThank you,\n{sender_name}')
    return {'connected': bool(account and account['connected_at']), 'email': account['email'] if account else user.email,
        'resume_name': resume.original_filename if resume else None, 'sender_name': user.full_name,
        'subject': f'{role} opportunities — {user.full_name}', 'body': body,
        'imported_recipients': len(recipients(db, True, [])), 'daily_limit': max(1, settings.outreach_daily_limit)}


def render(value, recipient, user):
    for key, replacement in {'recruiter_name': recipient.get('recruiter_name'),
            'company': recipient.get('company'), 'sender_name': user.full_name}.items():
        value = value.replace('{' + key + '}', str(replacement or ''))
    return value


def preview(db, user, request):
    if request.template_id:
        from app.services.email_template_service import get_template
        template = get_template(db, user, request.template_id)
        if request.subject != template['subject'] or request.body != template['body']:
            raise HTTPException(409, 'Template changed or has unsaved edits. Select or save it again before previewing.')
    selected = recipients(db, request.all_imported, request.contact_ids, request.manual_emails)
    if not selected:
        raise HTTPException(422, 'No valid recruiter email addresses selected.')
    sample = selected[0]
    resume = db.query(Resume).filter_by(user_id=user.id, is_primary=True).first()
    if request.attach_resume and not resume:
        raise HTTPException(422, 'Upload and select a primary resume first.')
    checksum = ''
    if request.attach_resume:
        _, content = attachment(db, user)
        checksum = hashlib.sha256(content).hexdigest()
    account_email = db.execute(text('SELECT email FROM outreach_accounts WHERE user_id=:user'), {'user': user.id}).scalar()
    payload = json.dumps([str(user.id), str(request.template_id), account_email or user.email, user.full_name, request.subject, request.body,
        sorted((r['email'], r['recruiter_name'], r['company']) for r in selected), str(resume.id) if request.attach_resume else None,
        resume.original_filename if request.attach_resume else None, checksum])
    token = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {'recipient_count': len(selected), 'sample_recipient': sample['email'],
        'subject': render(request.subject, sample, user), 'body': render(request.body, sample, user),
        'resume_name': resume.original_filename if request.attach_resume and resume else None, 'preview_token': token}


def attachment(db, user):
    resume = db.query(Resume).filter_by(user_id=user.id, is_primary=True).first()
    if not resume:
        raise HTTPException(422, 'Select a primary resume first.')
    source = Path(resume.storage_path).resolve()
    if not source.is_file():
        raise HTTPException(422, 'Primary resume file is unavailable.')
    if source.stat().st_size > settings.max_resume_size_bytes:
        raise HTTPException(422, 'Resume exceeds the attachment size limit.')
    with source.open('rb') as stream:
        content = stream.read(settings.max_resume_size_bytes + 1)
    if len(content) > settings.max_resume_size_bytes:
        raise HTTPException(422, 'Resume exceeds the attachment size limit.')
    if not source.is_relative_to(Path(settings.resume_storage_dir).resolve()):
        # Older uploads can retain a previous installation's absolute path.
        # Accept only the owner's recorded upload with its original checksum.
        if source.name != resume.stored_filename or not resume.checksum_sha256 or not hmac.compare_digest(
                hashlib.sha256(content).hexdigest(), resume.checksum_sha256):
            raise HTTPException(422, 'Primary resume file could not be verified.')
    return resume, content


def queue(db, user, request):
    # Serialize per-user idempotency and message deduplication.
    db.query(User).filter_by(id=user.id).with_for_update().one()
    existing = db.execute(text('SELECT id FROM outreach_campaigns WHERE user_id=:user AND request_key=:key'),
        {'user': user.id, 'key': request.request_key}).scalar()
    if existing:
        return {'id': existing, 'queued': 0, 'already_queued': True}
    if not request.template_id:
        raise HTTPException(422, 'Select a saved email template before sending.')
    from app.services.email_template_service import get_template
    template = get_template(db, user, request.template_id, lock=True)
    account = db.execute(text('SELECT email,connected_at FROM outreach_accounts WHERE user_id=:user'), {'user': user.id}).mappings().first()
    if not account or not account['connected_at']:
        raise HTTPException(409, 'Connect your sending email account first.')
    checked = preview(db, user, request)
    if not request.preview_token or not hmac.compare_digest(request.preview_token, checked['preview_token']):
        raise HTTPException(409, 'Message, recipients or resume changed. Review the preview again.')
    selected = recipients(db, request.all_imported, request.contact_ids, request.manual_emails)
    campaign_id = uuid.uuid4()
    path, name, checksum = None, None, ''
    if request.attach_resume:
        resume, content = attachment(db, user)
        source = Path(resume.storage_path).resolve()
        checksum = hashlib.sha256(content).hexdigest()
        STORAGE.mkdir(parents=True, exist_ok=True)
        target = STORAGE / (str(campaign_id) + source.suffix)
        target.write_bytes(content)
        path, name = str(target), resume.original_filename
    db.execute(text('''INSERT INTO outreach_campaigns (id,user_id,request_key,subject,body,sender_email,sender_name,resume_path,resume_name,resume_sha256,template_id,template_name)
        VALUES (:id,:user,:key,:subject,:body,:sender,:sender_name,:path,:name,:hash,:template_id,:template_name)'''),
        {'id': campaign_id, 'user': user.id, 'key': request.request_key, 'subject': request.subject,
         'body': request.body, 'sender': account['email'], 'sender_name': user.full_name, 'path': path, 'name': name, 'hash': checksum,
         'template_id': request.template_id, 'template_name': template['name']})
    queued = 0
    for recipient in selected:
        fingerprint = hashlib.sha256((recipient['email'] + '\0' + request.subject + '\0' + request.body + '\0' + checksum).encode()).hexdigest()
        queued += db.execute(text('''INSERT INTO outreach_messages (id,user_id,campaign_id,email,recruiter_name,company,fingerprint,rendered_subject,rendered_body)
            VALUES (:id,:user,:campaign,:email,:recruiter_name,:company,:fingerprint,:subject,:body)
            ON CONFLICT(user_id,fingerprint) DO NOTHING'''),
            {'id': uuid.uuid4(), 'user': user.id, 'campaign': campaign_id, **recipient, 'fingerprint': fingerprint,
             'subject': render(request.subject, recipient, user), 'body': render(request.body, recipient, user)}).rowcount
    db.commit()
    return {'id': campaign_id, 'queued': queued, 'duplicates_skipped': len(selected) - queued}


def history(db, user):
    return [dict(row) for row in db.execute(text('''SELECT c.id,c.subject,c.sender_email,c.template_name,c.created_at,c.cancelled,
        count(m.id) AS total, count(m.id) FILTER(WHERE m.status='sent') AS sent,
        count(m.id) FILTER(WHERE m.status='queued') AS queued,
        count(m.id) FILTER(WHERE m.status='failed') AS failed,
        array_remove(array_agg(DISTINCT m.error),NULL) AS errors,
        count(m.id) FILTER(WHERE m.status IN ('sending','unknown')) AS pending_verification
        FROM outreach_campaigns c LEFT JOIN outreach_messages m ON m.campaign_id=c.id
        WHERE c.user_id=:user GROUP BY c.id ORDER BY c.created_at DESC LIMIT 20'''), {'user': user.id}).mappings()]


def send_one():
    with engine.connect() as lock:
        if not lock.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': LOCK_ID}):
            return
        try:
            with SessionLocal() as db:
                # A crash after SMTP acceptance is ambiguous. Never resend it automatically.
                db.execute(text("UPDATE outreach_messages SET status='unknown',error='Delivery interrupted; check Sent mail before retrying.' WHERE status='sending'"))
                db.commit()
                row = db.execute(text('''SELECT m.*,c.sender_name,c.resume_path,c.resume_name,c.resume_sha256,
                    a.email AS sender,a.secret_ciphertext FROM outreach_messages m
                    JOIN outreach_campaigns c ON c.id=m.campaign_id JOIN outreach_accounts a ON a.user_id=m.user_id AND a.email=c.sender_email
                    JOIN users u ON u.id=m.user_id AND u.is_active
                    WHERE m.status='queued' AND NOT c.cancelled AND a.connected_at IS NOT NULL
                    AND (a.paused_until IS NULL OR a.paused_until<=now())
                    AND (SELECT count(*) FROM outreach_messages recent WHERE recent.user_id=m.user_id
                         AND recent.started_at > now()-interval '24 hours') < :limit
                    ORDER BY m.created_at LIMIT 1'''), {'limit': max(1, settings.outreach_daily_limit)}).mappings().first()
                if not row:
                    return
                user = db.get(User, row['user_id'])
                if not user or not user.is_active:
                    return
                try:
                    message = EmailMessage()
                    message['From'] = formataddr((row['sender_name'], row['sender']))
                    message['To'] = row['email']
                    message['Subject'] = row['rendered_subject']
                    message['Message-ID'] = make_msgid(idstring=str(row['id']))
                    message.set_content(row['rendered_body'])
                    if row['resume_path']:
                        attachment_path = Path(row['resume_path']).resolve()
                        if not attachment_path.is_relative_to(STORAGE.resolve()):
                            raise ValueError('Invalid attachment')
                        content = attachment_path.read_bytes()
                        if hashlib.sha256(content).hexdigest() != row['resume_sha256']:
                            raise ValueError('Attachment changed')
                        mime = mimetypes.guess_type(row['resume_name'])[0] or 'application/octet-stream'
                        main, sub = mime.split('/', 1)
                        message.add_attachment(content, maintype=main, subtype=sub, filename=row['resume_name'])
                    password = cipher().decrypt(row['secret_ciphertext'].encode()).decode()
                except InvalidToken:
                    db.execute(text('UPDATE outreach_accounts SET connected_at=NULL WHERE user_id=:user'), {'user': row['user_id']})
                    db.execute(text("UPDATE outreach_messages SET error='Reconnect your sending account after the server key changed.' WHERE id=:id"), {'id': row['id']})
                    db.commit()
                    return
                except Exception:
                    db.execute(text("UPDATE outreach_messages SET status='failed',error='Unable to prepare email or resume attachment.' WHERE id=:id"), {'id': row['id']})
                    db.commit()
                    return
                claimed = db.execute(text("""UPDATE outreach_messages m SET status='sending',started_at=now()
                    WHERE id=:id AND status='queued' AND EXISTS(SELECT 1 FROM outreach_campaigns c WHERE c.id=m.campaign_id AND NOT c.cancelled)"""), {'id': row['id']}).rowcount
                db.commit()
                if not claimed:
                    return
                try:
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ssl.create_default_context(), timeout=20) as smtp:
                        smtp.login(row['sender'], password)
                        refused = smtp.send_message(message)
                        if refused:
                            raise smtplib.SMTPRecipientsRefused(refused)
                    db.execute(text("UPDATE outreach_messages SET status='sent',sent_at=now(),error=NULL WHERE id=:id"), {'id': row['id']})
                except smtplib.SMTPAuthenticationError:
                    db.execute(text('UPDATE outreach_accounts SET connected_at=NULL WHERE user_id=:user'), {'user': row['user_id']})
                    db.execute(text("UPDATE outreach_messages SET status='queued',error='Reconnect the sending account.' WHERE id=:id"), {'id': row['id']})
                except smtplib.SMTPResponseException as exc:
                    quota = b'limit' in (exc.smtp_error or b'').lower() or b'quota' in (exc.smtp_error or b'').lower()
                    if 400 <= exc.smtp_code < 500 or quota:
                        db.execute(text("UPDATE outreach_accounts SET paused_until=now()+interval '1 hour' WHERE user_id=:user"), {'user': row['user_id']})
                        db.execute(text("UPDATE outreach_messages SET status='queued',error='Provider temporarily unavailable; sending paused for one hour.' WHERE id=:id"), {'id': row['id']})
                    else:
                        db.execute(text("UPDATE outreach_messages SET status='failed',error='Email provider rejected the message.' WHERE id=:id"), {'id': row['id']})
                except smtplib.SMTPRecipientsRefused:
                    db.execute(text("UPDATE outreach_messages SET status='failed',error='Recipient address rejected.' WHERE id=:id"), {'id': row['id']})
                except Exception:
                    db.execute(text("UPDATE outreach_messages SET status='unknown',error='Delivery uncertain; check Sent mail. Automatic retry disabled.' WHERE id=:id"), {'id': row['id']})
                db.commit()
        finally:
            lock.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': LOCK_ID})
            lock.commit()


def worker_loop(stop):
    while not stop.is_set():
        try:
            send_one()
        except Exception:
            logger.error('Recruiter email worker failed; check database migrations and configuration.')
        stop.wait(max(2, settings.outreach_interval_seconds))
