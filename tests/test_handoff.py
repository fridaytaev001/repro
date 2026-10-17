import hashlib
import io
import json
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.handoff import build_handoff
from app.main import create_app
from app.runs import CaseStore
from scripts.replay_case import run_fixture
from test_verification import candidate_case
from scripts.evaluate_live import cost_estimate


def report_case():
    return {'id': str(uuid4()), 'stage':'finished', 'outcome':'needs_information',
            'report':{'complaint':'Checkout behavior is unclear.', 'expected_behavior':'Need a published rule.'},
            'message':'Please specify the missing rule.'}


def test_bundle_hashes_evidence_and_labels_missing_replay(tmp_path):
    store = CaseStore(tmp_path)
    case = report_case()
    evidence = store.directory(case['id'])/'attempt'/'shot.png'
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b'actual-evidence')
    evidence_id = store.register(case, evidence, 'image/png')
    artifacts = build_handoff(store, case)
    with zipfile.ZipFile(store.artifact_path(case, artifacts['bundle'])[0]) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['missing'] and 'no candidate' in manifest['missing'][0]
        assert 'replay.json' not in archive.namelist()
        assert archive.read('evidence/'+evidence_id) == b'actual-evidence'
        for name, record in manifest['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == record['sha256']
        assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in archive.namelist())
    # A second export must not recursively include the previous bundle.
    again = build_handoff(store, case)
    with zipfile.ZipFile(store.artifact_path(case, again['bundle'])[0]) as archive:
        assert len([name for name in archive.namelist() if name.startswith('evidence/')]) == 1


def test_export_endpoint_contains_only_saved_case_and_rejects_active_case(tmp_path):
    case = report_case()
    store = CaseStore(tmp_path)
    store.save(case)
    with TestClient(create_app(tmp_path, enable_investigation=False)) as client:
        response = client.get(f"/api/runs/{case['id']}/exports/bundle")
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert json.loads(archive.read('report.json'))['id'] == case['id']
            assert not any('.env' in name for name in archive.namelist())
        assert client.get(f"/api/runs/{case['id']}/exports/unknown").status_code == 422
        case.update(stage='investigating')
        store.save(case)
        assert client.get(f"/api/runs/{case['id']}/exports/bundle").status_code == 409


@pytest.mark.browser
@pytest.mark.asyncio
async def test_exported_fixture_replays_and_opposite_assertions_are_explicit(tmp_path, live_server):
    store = CaseStore(tmp_path/'cases')
    case = candidate_case(live_server+'/')
    case.update(report={'complaint':'Coupon vanished.', 'expected_behavior':'Preserve SAVE10.'}, stage='finished')
    artifacts = build_handoff(store, case)
    with zipfile.ZipFile(store.artifact_path(case, artifacts['bundle'])[0]) as archive:
        fixture = tmp_path/'replay.json'
        fixture.write_bytes(archive.read('replay.json'))
        assert "== 'pass'" in archive.read('test_reproduce.py').decode()
        assert "== 'fail'" in archive.read('test_regression.py').decode()
    result = await run_fixture(fixture, live_server+'/', tmp_path/'replay-results')
    assert result['status'] == 'pass'
    assert result['violations'][-1]['actual_total_cents'] == 10000


@pytest.mark.asyncio
async def test_replay_rejects_foreign_url_before_browser_dispatch(tmp_path):
    case = candidate_case('https://example.com/')
    fixture = tmp_path/'fixture.json'
    fixture.write_text(json.dumps({'schema_version':1,'target_id':'demo-store',
        'acceptance':case['acceptance'],'candidate':case['candidate']}))
    with pytest.raises(ValueError, match='unsupported target'):
        await run_fixture(fixture, 'http://127.0.0.1:8000/', tmp_path/'results')


def test_cost_estimate_does_not_double_charge_cached_prompt_tokens():
    case = {'model':'deepseek-ai/Deepseek-V4-Flash', 'calls':[{'usage':{
        'prompt_tokens':1000000,'completion_tokens':1000000,'prompt_tokens_details':{'cached_tokens':500000}}}]}
    estimate = cost_estimate(case)
    assert estimate['usd_estimate'] == .365
    assert estimate['calls_with_unreported_cache'] == 0
    case['calls'][0]['usage']['prompt_tokens_details']['cached_tokens'] = 1000001
    assert cost_estimate(case) is None
