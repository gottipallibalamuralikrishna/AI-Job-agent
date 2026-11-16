from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException
from google.genai import errors

from app.services import gemini_resume_service as service


@pytest.fixture
def extractor(monkeypatch):
    monkeypatch.setattr(service.settings, 'gemini_model', 'primary')
    monkeypatch.setattr(service.settings, 'gemini_fallback_model', 'backup')
    instance = service.GeminiResumeService.__new__(service.GeminiResumeService)
    return instance


def api_error(code):
    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code, {'error': {'code': code, 'message': 'Private provider diagnostic'}})


@pytest.mark.parametrize('code', [408, 429, 500, 502, 503, 504])
def test_transient_failure_uses_backup(extractor, code):
    extractor._generate_content = Mock(side_effect=[api_error(code), SimpleNamespace(
        parsed={'professional_title': 'Frontend Developer'}, text=None)])
    assert extractor.extract_profile('Frontend Developer').professional_title == 'Frontend Developer'
    assert [call.args[0] for call in extractor._generate_content.call_args_list] == ['primary', 'backup']


@pytest.mark.parametrize('code', [400, 401, 403, 404])
def test_configuration_failure_does_not_try_backup(extractor, code):
    extractor._generate_content = Mock(side_effect=api_error(code))
    with pytest.raises(HTTPException) as failure:
        extractor.extract_profile('Frontend Developer')
    assert failure.value.status_code == 503
    assert 'configuration' in failure.value.detail
    assert extractor._generate_content.call_count == 1


@pytest.mark.parametrize('code,status', [(503, 503), (504, 503), (429, 429)])
def test_both_models_fail_with_useful_error(extractor, code, status):
    extractor._generate_content = Mock(side_effect=api_error(code))
    with pytest.raises(HTTPException) as failure:
        extractor.extract_profile('Frontend Developer')
    assert failure.value.status_code == status
    assert 'Your resume is saved' in failure.value.detail
    assert 'Private provider diagnostic' not in failure.value.detail
    assert 'Retry-After' in failure.value.headers
    assert extractor._generate_content.call_count == 2


def test_network_failure_uses_backup(extractor):
    extractor._generate_content = Mock(side_effect=[httpx.ReadTimeout('timeout'), SimpleNamespace(
        parsed={'professional_title': 'Developer'}, text=None)])
    assert extractor.extract_profile('Developer').professional_title == 'Developer'


def test_both_connections_fail(extractor):
    extractor._generate_content = Mock(side_effect=httpx.ConnectError('private diagnostic'))
    with pytest.raises(HTTPException) as failure:
        extractor.extract_profile('Developer')
    assert failure.value.status_code == 503
    assert 'Unable to reach' in failure.value.detail


@pytest.mark.parametrize('backup', [None, 'primary'])
def test_no_duplicate_fallback(extractor, monkeypatch, backup):
    monkeypatch.setattr(service.settings, 'gemini_fallback_model', backup)
    extractor._generate_content = Mock(side_effect=api_error(503))
    with pytest.raises(HTTPException):
        extractor.extract_profile('Developer')
    assert extractor._generate_content.call_count == 1
