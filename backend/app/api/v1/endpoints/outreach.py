from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import outreach_service as service
from app.services import email_template_service as templates

router = APIRouter(prefix='/outreach', tags=['Recruiter email'])


class Connection(BaseModel):
    email: EmailStr
    app_password: SecretStr


class Message(BaseModel):
    all_imported: bool = False
    contact_ids: list[UUID] = Field(default_factory=list, max_length=5000)
    manual_emails: list[EmailStr] = Field(default_factory=list, max_length=5000)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=10, max_length=20000)
    attach_resume: bool = True
    request_key: UUID
    preview_token: str | None = None
    template_id: UUID | None = None

    @field_validator('subject')
    @classmethod
    def single_line(cls, value):
        if '\r' in value or '\n' in value:
            raise ValueError('Subject must be one line')
        return value

    @model_validator(mode='after')
    def selection(self):
        if self.all_imported and self.contact_ids:
            raise ValueError('Choose all imported recruiters or individual contacts')
        if not self.all_imported and not self.contact_ids and not self.manual_emails:
            raise ValueError('Select recruiter contacts or enter email addresses')
        return self


@router.get('/context')
def get_context(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.context(db, user)


@router.get('/templates')
def list_templates(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return templates.list_templates(db, user)


@router.post('/templates', status_code=201)
def create_template(request: templates.TemplateInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return templates.save_template(db, user, request)


@router.post('/templates/upload', status_code=201)
async def upload_template(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        content = await file.read(131073)
        data = templates.parse_upload(file.filename, content)
        return templates.save_template(db, user, data)
    finally:
        await file.close()


@router.put('/templates/{template_id}')
def update_template(template_id: UUID, request: templates.TemplateInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return templates.save_template(db, user, request, template_id)


@router.delete('/templates/{template_id}')
def delete_template(template_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    templates.get_template(db, user, template_id)
    db.execute(text('DELETE FROM outreach_templates WHERE id=:id AND user_id=:user'), {'id': template_id, 'user': user.id})
    db.commit()
    return {'deleted': True}


@router.put('/connection')
def connect(request: Connection, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.connect_account(db, user, str(request.email), request.app_password.get_secret_value())
    return {'connected': True, 'email': str(request.email)}


@router.delete('/connection')
def disconnect(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.execute(text('DELETE FROM outreach_accounts WHERE user_id=:user'), {'user': user.id})
    db.commit()
    return {'connected': False}


@router.post('/preview')
def preview(request: Message, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.preview(db, user, request)


@router.post('/campaigns', status_code=202)
def queue(request: Message, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.queue(db, user, request)


@router.get('/campaigns')
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.history(db, user)


@router.post('/campaigns/{campaign_id}/cancel')
def cancel(campaign_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = db.execute(text('UPDATE outreach_campaigns SET cancelled=true WHERE id=:id AND user_id=:user'), {'id': campaign_id, 'user': user.id})
    if not result.rowcount:
        raise HTTPException(404, 'Campaign not found')
    db.execute(text("UPDATE outreach_messages SET status='cancelled' WHERE campaign_id=:id AND user_id=:user AND status='queued'"), {'id': campaign_id, 'user': user.id})
    db.commit()
    return {'cancelled': True}
