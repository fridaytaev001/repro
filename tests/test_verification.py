import asyncio
from copy import deepcopy
from uuid import uuid4

import pytest

from app.agents.verifier import Verifier, acceptance_hash, money
from app.agents.coordinator import RunManager
from app.runs import CaseStore
from app.settings import Settings


def candidate_case(url, coupon='SAVE10', edit=True):
    acceptance = {'version': 1, 'checks': [{'id': 'coupon-preserved',
        'description': 'Address edits preserve the valid SAVE10 discount.',
        'observable': 'Visible total and coupon', 'expected': 'Retain SAVE10',
        'rule_source': 'store-rules:v1'}], 'assumptions': []}
    acceptance['hash'] = acceptance_hash(acceptance)
    def click(name, html_id=None):
        return {'action': 'click', 'target': {'tag': 'button', 'name': name, 'html_id': html_id}}
    steps = [{'action': 'open', 'url': url}, click('Your bag 1', 'open-cart'),
        {'action': 'fill', 'target': {'tag': 'input', 'name': 'Have a little something?', 'html_id': 'coupon'}, 'value': coupon},
        click('Apply'), click('Continue to review', 'continue-review')]
    if edit:
        steps += [click('Edit address', 'edit-address'),
            {'action': 'fill', 'target': {'tag': 'input', 'name': 'Street address', 'html_id': None}, 'value': '500 Pine Street'},
            click('Save address', 'continue-review')]
    return {'id': str(uuid4()), 'stage': 'awaiting_verification', 'outcome': None,
        'acceptance': acceptance, 'execution_mode': 'test',
        'candidate': {'summary': 'Claimed coupon loss.', 'steps': steps,
            'acceptance_hash': acceptance['hash'], 'acceptance_version': 1}}


@pytest.mark.browser
@pytest.mark.asyncio
async def test_independent_replay_confirms_actual_rule_violation(tmp_path, live_server):
    store = CaseStore(tmp_path)
    case = candidate_case(live_server + '/')
    result = await Verifier(store, case, Settings(target_url=live_server+'/')).run()
    assert result['status'] == 'pass'
    assert case['outcome'] == 'confirmed'
    assert result['initial_session_storage_empty'] and result['initial_cookies_empty']
    assert result['violations'][-1]['expected_total_cents'] == 9000
    assert result['violations'][-1]['actual_total_cents'] == 10000
    assert any(row['values']['total'] == '$90.00' for row in result['observations'])
    assert store.artifact_path(case, result['violations'][0]['evidence_id'])[0].exists()
    assert any(a['media_type'] == 'application/zip' for a in case['artifacts'].values())


@pytest.mark.browser
@pytest.mark.asyncio
@pytest.mark.parametrize('coupon,edit', [('VIP20', True), ('SAVE10', False)])
async def test_wrong_candidate_and_expected_ineligibility_cannot_confirm(tmp_path, live_server, coupon, edit):
    case = candidate_case(live_server+'/', coupon, edit)
    result = await Verifier(CaseStore(tmp_path), case, Settings(target_url=live_server+'/')).run()
    assert result['status'] == 'fail'
    assert case['outcome'] == 'not_reproduced'
    assert result['violations'] == []


@pytest.mark.asyncio
async def test_changed_criteria_never_launch_a_browser(tmp_path):
    case = candidate_case('http://127.0.0.1:8000/')
    case['acceptance']['checks'][0]['expected'] = 'Weakened criterion'
    def forbidden_browser(*args, **kwargs):
        pytest.fail('Browser must not start for changed criteria')
    result = await Verifier(CaseStore(tmp_path), case, Settings(), forbidden_browser).run()
    assert result['status'] == 'inconclusive'
    assert case['outcome'] == 'blocked'
    assert result['action_count'] == 0


@pytest.mark.browser
@pytest.mark.asyncio
async def test_missing_target_is_inconclusive_not_a_confirmed_bug(tmp_path, live_server):
    case = candidate_case(live_server+'/')
    case['candidate']['steps'][1]['target']['html_id'] = 'does-not-exist'
    result = await Verifier(CaseStore(tmp_path), case, Settings(target_url=live_server+'/')).run()
    assert result['status'] == 'inconclusive'
    assert case['outcome'] == 'blocked'
    assert 'target' in result['reason']


@pytest.mark.asyncio
async def test_terminal_cancel_is_idempotent_and_preserves_confirmation(tmp_path):
    store = CaseStore(tmp_path)
    case = candidate_case('http://127.0.0.1:8000/')
    case.update(stage='finished', outcome='confirmed')
    store.save(case)
    manager = RunManager(store, lambda: Settings())
    before = deepcopy(case)
    manager.cancel(case)
    manager.cancel(case)
    assert case == before
    with pytest.raises(ValueError, match='already independently confirmed'):
        manager.enqueue(case, verification_only=True)


@pytest.mark.asyncio
async def test_verification_admission_does_not_require_provider_key(tmp_path):
    manager = RunManager(CaseStore(tmp_path), lambda: Settings())
    case = candidate_case('http://127.0.0.1:8000/')
    manager.enqueue(case, verification_only=True)
    assert case['stage'] == 'queued'
    assert case['id'] in manager.verification_jobs
    manager.cancel(case)
    count = case['event_count']
    manager.cancel(case)
    assert case['event_count'] == count


def test_money_parsing_rejects_unexpected_format():
    assert money('−$10.00') == 1000
    assert money('$1,000.00') == 100000
    with pytest.raises(ValueError):
        money('USD NaN')


@pytest.mark.asyncio
async def test_over_budget_replay_is_rejected_before_browser_start(tmp_path):
    case = candidate_case('http://127.0.0.1:8000/')
    def forbidden_browser(*args, **kwargs):
        pytest.fail('Over-budget replay must never dispatch browser work')
    result = await Verifier(CaseStore(tmp_path), case, Settings(max_actions=1), forbidden_browser).run()
    assert result['action_count'] == 0
    assert result['status'] == 'inconclusive'
    assert case['stop_reason'] == 'verification_inconclusive'


@pytest.mark.asyncio
async def test_verifier_cancel_stops_dispatch_and_preserves_receipt(tmp_path):
    entered = asyncio.Event()
    operations = []
    class BlockingBrowser:
        def __init__(self, *args, **kwargs):
            pass
        async def start(self):
            operations.append('start')
            entered.set()
            await asyncio.Event().wait()
        async def close(self):
            operations.append('closed')
    store = CaseStore(tmp_path)
    case = candidate_case('http://127.0.0.1:8000/')
    task = asyncio.create_task(Verifier(store, case, Settings(), BlockingBrowser).run())
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    saved = store.read(case['id'])
    assert operations == ['start', 'closed']
    assert saved['verification']['status'] == 'inconclusive'
    assert saved['verification']['action_count'] == 0
    assert saved['outcome'] is None


@pytest.mark.asyncio
async def test_verifier_timeout_is_inconclusive_and_closes_browser(tmp_path):
    operations = []
    class BlockingBrowser:
        def __init__(self, *args, **kwargs):
            pass
        async def start(self):
            await asyncio.Event().wait()
        async def close(self):
            operations.append('closed')
    case = candidate_case('http://127.0.0.1:8000/')
    result = await Verifier(CaseStore(tmp_path), case,
        Settings(verification_timeout_seconds=.01), BlockingBrowser).run()
    assert result['status'] == 'inconclusive'
    assert operations == ['closed']
    assert case['outcome'] == 'blocked'
