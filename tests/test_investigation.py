import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.coordinator import Investigation, RunManager
from app.main import create_app
from app.providers.crusoe import ProviderError
from app.runs import CaseStore
from app.settings import Settings
from app.tools.browser import BrowserAction, BrowserSession


def case_fixture():
    return {'id': str(uuid4()), 'stage': 'received', 'created_at': '2026-10-17T20:00:00Z',
            'report': {'complaint': 'Discount disappeared.', 'expected_behavior': 'Preserve discount.', 'steps': ''}}


CHECKS = {'checks': [{'id': 'preserve-coupon', 'description': 'Preserve valid discount across address changes.',
          'observable': 'Displayed discount', 'expected': 'SAVE10 remains 10% of merchandise subtotal.',
          'rule_source': 'store-rules:v1'}], 'assumptions': []}
HYPOTHESIS = {'statement': 'An address transition may drop the coupon.',
              'experiment': 'Apply coupon and enter shipping details.'}


class TestBrowser:
    __test__ = False

    def __init__(self, target, directory, on_artifact=None):
        self.replay = []
        self.target = target

    async def start(self):
        pass

    async def close(self):
        pass

    async def execute(self, action):
        record = {'action': action.action}
        self.replay.append(record)
        return {'executed_action': record, 'observation': {'text': '$90.00', 'elements': []}, 'evidence_id': 'test-evidence'}


@pytest.mark.asyncio
async def test_frozen_checks_and_unexecuted_candidate_evidence_are_rejected(tmp_path):
    case = case_fixture()
    run = Investigation(CaseStore(tmp_path), case, Settings())
    browser = TestBrowser('', tmp_path)
    with pytest.raises(ValueError, match='Define acceptance'):
        await run.tool('browser', {'action': 'inspect'}, browser)
    await run.tool('define_checks', CHECKS, browser)
    original_hash = case['acceptance']['hash']
    with pytest.raises(ValueError, match='frozen'):
        await run.tool('define_checks', CHECKS, browser)
    assert case['acceptance']['hash'] == original_hash
    await run.tool('hypothesis', HYPOTHESIS, browser)
    with pytest.raises(ValueError, match='screenshots'):
        await run.tool('candidate', {'summary': 'Discount went away on screen.',
            'expected_behavior': 'Preserve discount', 'observed_behavior': 'No discount',
            'evidence_ids': ['invented-before', 'invented-after']}, browser)
    assert not case.get('candidate')


@pytest.mark.asyncio
async def test_no_progress_requires_a_new_hypothesis(tmp_path):
    case = case_fixture()
    run = Investigation(CaseStore(tmp_path), case, Settings())
    browser = TestBrowser('', tmp_path)
    await run.tool('define_checks', CHECKS, browser)
    await run.tool('hypothesis', HYPOTHESIS, browser)
    await run.tool('browser', {'action': 'inspect'}, browser)
    result = await run.tool('browser', {'action': 'inspect'}, browser)
    assert result['replan_required'] is True
    with pytest.raises(ValueError, match='Repeated no-progress'):
        await run.tool('browser', {'action': 'click', 'element_id': 'e1'}, browser)
    await run.tool('hypothesis', {'statement': 'A later navigation step may drop the coupon.',
        'experiment': 'Try a different navigation sequence after review.',
        'prior_result': 'Initial address entry retained the discount.'}, browser)
    assert run.must_replan is False


@pytest.mark.asyncio
async def test_a_candidate_cannot_be_promoted_to_confirmed(tmp_path):
    case = case_fixture()
    run = Investigation(CaseStore(tmp_path), case, Settings())
    browser = TestBrowser('', tmp_path)
    await run.tool('define_checks', CHECKS, browser)
    await run.tool('hypothesis', HYPOTHESIS, browser)
    browser.replay = [{'action': 'click', 'target': {'name': 'Review'}}]
    run.current_evidence = {'before', 'after'}
    result = await run.tool('candidate', {'summary': 'Coupon disappears during checkout.',
        'expected_behavior': '$90.00', 'observed_behavior': '$100.00',
        'evidence_ids': ['before', 'after']}, browser)
    assert result['confirmed'] is False
    assert case['outcome'] is None
    assert case['stage'] == 'awaiting_verification'
    assert case['candidate']['steps'] == browser.replay


def test_arbitrary_browser_code_and_unapproved_urls_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        BrowserAction.model_validate({'action': 'evaluate', 'javascript': 'fetch(secret)'})
    browser = BrowserSession('http://127.0.0.1:8000/', tmp_path)
    assert browser.allowed_url('http://127.0.0.1:8000/', True)
    assert not browser.allowed_url('http://127.0.0.1:8000.evil.example/', True)
    assert not browser.allowed_url('http://127.0.0.1:8000/api/reports')
    assert not browser.allowed_url('http://127.0.0.1:8000/static/case.js', True)
    assert not browser.allowed_url('http://127.0.0.1:8000/?secret=anything', True)


def test_missing_key_saves_a_blocked_case_and_never_claims_live(tmp_path):
    app = create_app(tmp_path, settings_factory=lambda: Settings())
    with TestClient(app) as client:
        created = client.post('/api/reports', json={'complaint': 'Discount disappeared.',
            'expected_behavior': 'Coupon should remain.', 'page_url': 'http://127.0.0.1:8000/'}).json()
        case = client.get(created['api_url']).json()
        assert case['outcome'] == 'blocked'
        assert case['stop_reason'] == 'missing_key'
        assert case['execution_mode'] == 'unavailable'
        assert client.get(created['api_url']+'/events').json()['events'][0]['type'] == 'blocked'


@pytest.mark.asyncio
async def test_queue_bound_and_duplicate_admission(tmp_path):
    store = CaseStore(tmp_path)
    manager = RunManager(store, lambda: Settings(api_key='synthetic', queue_size=1))
    first, second = case_fixture(), case_fixture()
    manager.enqueue(first)
    with pytest.raises(ValueError, match='already'):
        manager.enqueue(first)
    with pytest.raises(asyncio.QueueFull):
        manager.enqueue(second)
    assert manager.queue.qsize() == 1
    manager.cancel(first)
    assert store.read(first['id'])['stop_reason'] == 'cancelled_by_user'


@pytest.mark.asyncio
async def test_restart_marks_interrupted_work_without_erasing_evidence(tmp_path):
    store = CaseStore(tmp_path)
    case = case_fixture()
    case['stage'] = 'investigating'
    store.event(case, 'browser_action', 'Saved observation.')
    manager = RunManager(store)
    await manager.start()
    try:
        restarted = store.read(case['id'])
        assert restarted['stop_reason'] == 'worker_interrupted'
        assert store.events(case['id'])[0]['summary'] == 'Saved observation.'
    finally:
        await manager.close()


def test_artifact_registration_rejects_escape_and_names_across_attempts_are_unique(tmp_path):
    store = CaseStore(tmp_path)
    case = case_fixture()
    with pytest.raises(ValueError, match='escaped'):
        store.register(case, tmp_path / 'outside.png', 'image/png')
    first = store.directory(case['id']) / 'attempt-one' / 'screenshot-001.png'
    second = store.directory(case['id']) / 'attempt-two' / 'screenshot-001.png'
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_bytes(b'first')
    second.write_bytes(b'second')
    first_id = store.register(case, first, 'image/png')
    second_id = store.register(case, second, 'image/png')
    assert first_id != second_id
    assert store.artifact_path(case, first_id)[0].read_bytes() == b'first'


@pytest.mark.asyncio
async def test_active_cancellation_preserves_worker_for_the_next_case(tmp_path):
    closed = []

    class BlockingProvider:
        execution_mode = 'test'

        def __init__(self, settings, on_request=None):
            pass

        async def discover(self):
            await asyncio.Event().wait()

        async def close(self):
            closed.append(True)

    store = CaseStore(tmp_path)
    manager = RunManager(store, lambda: Settings(api_key='synthetic'), BlockingProvider, TestBrowser)
    await manager.start()
    try:
        case = case_fixture()
        manager.enqueue(case)
        for _ in range(100):
            if manager.active_id:
                break
            await asyncio.sleep(.01)
        assert manager.active_id == case['id']
        manager.cancel(store.read(case['id']))
        await asyncio.wait_for(manager.queue.join(), 2)
        assert store.read(case['id'])['stop_reason'] == 'cancelled_by_user'
        assert closed
        assert not manager.worker.done()
    finally:
        await manager.close()
