import json
import uuid
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text


class TemplateInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=10, max_length=20000)

    @field_validator('subject')
    @classmethod
    def header(cls, value):
        if '\n' in value or '\r' in value:
            raise ValueError('Subject must be a single line')
        return value


def list_templates(db, user):
    return [dict(row) for row in db.execute(text('SELECT * FROM outreach_templates WHERE user_id=:user ORDER BY updated_at DESC,id'), {'user': user.id}).mappings()]


def get_template(db, user, template_id, lock=False):
    row = db.execute(text('SELECT * FROM outreach_templates WHERE id=:id AND user_id=:user' + (' FOR SHARE' if lock else '')), {'id': template_id, 'user': user.id}).mappings().first()
    if not row:
        raise HTTPException(404, 'Email template not found.')
    return dict(row)


def save_template(db, user, data, template_id=None):
    if template_id:
        get_template(db, user, template_id)
        db.execute(text('UPDATE outreach_templates SET name=:name,subject=:subject,body=:body,updated_at=now() WHERE id=:id AND user_id=:user'),
            {'id': template_id, 'user': user.id, **data.model_dump()})
    else:
        template_id = uuid.uuid4()
        db.execute(text('INSERT INTO outreach_templates(id,user_id,name,subject,body) VALUES(:id,:user,:name,:subject,:body)'),
            {'id': template_id, 'user': user.id, **data.model_dump()})
    db.commit()
    return get_template(db, user, template_id)


def parse_upload(filename, content):
    if len(content) > 131072:
        raise HTTPException(413, 'Template file must be smaller than 128 KB.')
    suffix = Path(filename or '').suffix.lower()
    if suffix not in {'.txt', '.json'}:
        raise HTTPException(415, 'Upload a UTF-8 .txt or .json email template.')
    try:
        value = content.decode('utf-8-sig')
        if suffix == '.json':
            data = json.loads(value)
        else:
            lines = value.splitlines()
            if not lines or not lines[0].lower().startswith('subject:'):
                raise ValueError('Missing Subject header')
            data = {'name': Path(filename).stem[:100], 'subject': lines[0].split(':', 1)[1].strip(),
                    'body': '\n'.join(lines[1:]).strip()}
        return TemplateInput.model_validate(data)
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, 'Invalid template. Use name, subject and body in JSON, or Subject: on the first line of a text file, followed by the message body.') from exc
