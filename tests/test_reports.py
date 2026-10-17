from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def payload(**changes):
    return {"complaint": "My discount disappeared.",
            "expected_behavior": "My valid coupon should remain.",
            "page_url": "http://127.0.0.1:8000/?email=private@example.com#secret", **changes}


def test_report_is_durable_and_url_does_not_retain_query(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.post('/api/reports', json=payload(complaint='  Discount disappeared.  '))
        assert response.status_code == 202
        created = response.json()
        assert created['case_id'] in created['status_url']
    # A different application instance must read the persisted receipt.
    with TestClient(create_app(tmp_path)) as restarted:
        case = restarted.get(created['api_url']).json()
        assert case['report']['complaint'] == 'Discount disappeared.'
        assert case['report']['page_url'] == 'http://127.0.0.1:8000/'
        assert case['stage'] == 'received'
        assert case['outcome'] is None
        assert case['investigation_enabled'] is False
        assert len(list(tmp_path.glob('*.json'))) == 1


@pytest.mark.parametrize('changes', [
    {'complaint': '      '}, {'expected_behavior': ''}, {'complaint': 'x' * 4001},
    {'target_id': 'production'}, {'page_url': 'https://example.com/'},
    {'page_url': 'http://127.0.0.1:8000.evil.example/'},
    {'page_url': 'http://user:pass@127.0.0.1:8000/'},
    {'page_url': 'javascript:alert(1)'}, {'page_url': 'http://127.0.0.1:8000/admin'},
])
def test_invalid_reports_are_rejected_without_creating_files(tmp_path, changes):
    with TestClient(create_app(tmp_path)) as client:
        assert client.post('/api/reports', json=payload(**changes)).status_code == 422
        assert not list(tmp_path.iterdir())


def test_case_lookup_is_bounded_and_does_not_leak_files(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get(f'/api/runs/{uuid4()}').status_code == 404
        assert client.get('/api/runs/not-a-uuid').status_code == 422


def test_unwritable_storage_does_not_return_false_success(tmp_path):
    storage_file = tmp_path / 'not-a-directory'
    storage_file.write_text('fixture')
    with TestClient(create_app(storage_file)) as client:
        assert client.post('/api/reports', json=payload()).status_code == 503


def test_broken_case_file_is_not_reported_as_success(tmp_path):
    case_id = uuid4()
    (tmp_path / f'{case_id}.json').write_text('{broken')
    with TestClient(create_app(tmp_path)) as client:
        assert client.get(f'/api/runs/{case_id}').status_code == 503
