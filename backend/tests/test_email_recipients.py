import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text

from app.api.v1.endpoints.outreach import Message
from app.services import outreach_service as service
from tests.test_collection_flow import db
from tests.test_outreach import setup, approved, request


def test_manual_addresses_can_be_used_without_saved_contacts():
    data = request().model_dump()
    data.update(all_imported=False, manual_emails=['hr@example.com'])
    assert Message(**data).manual_emails == ['hr@example.com']


@pytest.mark.parametrize('addresses', [[], ['invalid'], ['hr@example.com\r\nBcc:other@example.com']])
def test_empty_or_invalid_manual_selection_is_rejected(addresses):
    data = request().model_dump()
    data.update(all_imported=False, manual_emails=addresses)
    with pytest.raises(ValidationError):
        Message(**data)


def test_selected_and_manual_addresses_are_deduplicated_with_saved_names(db, setup):
    user, _, contacts, _ = setup
    message = approved(db, user)
    message.all_imported = False
    message.contact_ids = [contacts[0].id]
    message.manual_emails = ['FIRST@example.com', 'new@example.com', 'new@example.com']
    selected = service.recipients(db, False, message.contact_ids, message.manual_emails)
    assert len(selected) == 2
    assert selected[0]['company'] == 'Example'
    message.preview_token = service.preview(db, user, message)['preview_token']
    assert service.queue(db, user, message)['queued'] == 2
    emails = set(db.execute(text('SELECT email FROM outreach_messages')).scalars())
    assert emails == {'first@example.com', 'new@example.com'}


def test_changing_manual_addresses_requires_a_new_preview(db, setup):
    user, _, _, _ = setup
    message = approved(db, user)
    message.all_imported = False
    message.manual_emails = ['first-manual@example.com']
    message.preview_token = service.preview(db, user, message)['preview_token']
    message.manual_emails = ['different@example.com']
    with pytest.raises(HTTPException) as exc:
        service.queue(db, user, message)
    assert exc.value.status_code == 409
    assert db.execute(text('SELECT count(*) FROM outreach_messages')).scalar() == 0


def test_manual_only_recipient_uses_generic_personalization(db, setup):
    user, _, _, _ = setup
    message = approved(db, user)
    message.all_imported = False
    message.manual_emails = ['manual@example.com']
    preview = service.preview(db, user, message)
    assert preview['recipient_count'] == 1
    assert 'your organisation' in preview['subject']
    message.preview_token = preview['preview_token']
    assert service.queue(db, user, message)['queued'] == 1


def test_all_imported_plus_manual_is_supported(db, setup):
    user, _, _, _ = setup
    message = approved(db, user)
    message.manual_emails = ['new@example.com', 'first@example.com']
    assert service.preview(db, user, message)['recipient_count'] == 3
