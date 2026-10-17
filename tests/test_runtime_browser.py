"""Protected integration tests. The scripted provider is TEST mode, never live."""
import json
from uuid import uuid4

import pytest

from app.agents.coordinator import Investigation
from app.runs import CaseStore
from app.settings import Settings
from app.tools.browser import BrowserSession, BrowserAction

pytestmark = [pytest.mark.browser, pytest.mark.asyncio]


class ScriptedProvider:
    execution_mode = 'test'
    provider_name = 'Scripted test provider'

    def __init__(self, settings, on_request=None):
        self.on_request = on_request
        self.index = 0
        self.observation = None
        self.evidence = []

    async def discover(self):
        self.on_request('request', {'operation': 'test-catalog', 'attempt': 1})
        return {'id': 'scripted-test-model'}

    async def close(self):
        pass

    def control(self, name):
        return next(item['id'] for item in self.observation['elements'] if name in item['name'])

    async def chat(self, messages, tools):
        self.on_request('request', {'operation': 'test-completion', 'attempt': 1})
        if messages[-1]['role'] == 'tool':
            latest = json.loads(messages[-1]['content'])
            assert 'error' not in latest, latest
            if 'observation' in latest:
                self.observation = latest['observation']
                self.evidence.append(latest['evidence_id'])
        steps = [
            ('define_checks', lambda: {'checks': [{'id': 'coupon-preserved',
                'description': 'Address edits preserve a valid coupon.', 'observable': 'Displayed discount and total',
                'expected': 'SAVE10 remains applied after address-only edits.', 'rule_source': 'store-rules:v1'}]}),
            ('hypothesis', lambda: {'statement': 'Initial shipping entry may discard the coupon.',
                'experiment': 'Apply SAVE10 and proceed through initial shipping entry.'}),
            ('browser', lambda: {'action': 'inspect'}),
            ('browser', lambda: {'action': 'click', 'element_id': self.control('Your bag')}),
            ('browser', lambda: {'action': 'fill', 'element_id': self.control('Have a little something?'), 'value': 'SAVE10'}),
            ('browser', lambda: {'action': 'click', 'element_id': self.control('Apply')}),
            ('browser', lambda: {'action': 'click', 'element_id': self.control('Continue to review')}),
            ('hypothesis', lambda: {'statement': 'Returning from review to edit an address may discard the coupon.',
                'experiment': 'Edit the street address from review and save it.',
                'prior_result': 'Initial shipping entry retained the $90.00 total.'}),
            ('browser', lambda: {'action': 'click', 'element_id': self.control('Edit address')}),
            ('browser', lambda: {'action': 'fill', 'element_id': self.control('Street address'), 'value': '200 Pine Street'}),
            ('browser', lambda: {'action': 'click', 'element_id': self.control('Save address')}),
            ('candidate', lambda: {'summary': 'Discount disappeared after address edit from review.',
                'expected_behavior': 'SAVE10 keeps the total at $90.00.',
                'observed_behavior': 'The total changed to $100.00 and the discount row disappeared.',
                'evidence_ids': self.evidence[-2:]}),
        ]
        name, arguments = steps[self.index]
        self.index += 1
        return {'message': {'role': 'assistant', 'content': None, 'tool_calls': [{
            'id': f'test-call-{self.index}', 'type': 'function',
            'function': {'name': name, 'arguments': json.dumps(arguments())}}]},
            'usage': {'total_tokens': 100}, 'request_id': f'test-request-{self.index}',
            'response_id': f'test-response-{self.index}', 'model': 'scripted-test-model', 'finish_reason': 'tool_calls'}


async def test_loop_uses_real_browser_records_recovery_and_stops_at_candidate(tmp_path, live_server):
    store = CaseStore(tmp_path)
    case = {'id': str(uuid4()), 'report': {'complaint': 'My discount disappeared when changing my address.',
            'expected_behavior': 'My valid coupon should remain.', 'steps': ''}}
    run = Investigation(store, case, Settings(api_key='synthetic-test-only', target_url=live_server+'/'),
                        provider_factory=ScriptedProvider)
    await run.run()
    saved = store.read(case['id'])
    assert saved['stage'] == 'awaiting_verification'
    assert saved['outcome'] is None
    assert saved['execution_mode'] == 'test'
    assert len(saved['hypotheses']) == 2
    assert saved['browser_action_count'] == 8
    assert saved['candidate']['observed_behavior'].startswith('The total changed to $100.00')
    assert saved['candidate']['steps'][-1]['target']['html_id'] == 'continue-review'
    assert len(saved['candidate']['evidence_ids']) == 2
    for artifact_id in saved['candidate']['evidence_ids']:
        path, media_type = store.artifact_path(saved, artifact_id)
        assert path.read_bytes().startswith(b'\x89PNG')
        assert media_type == 'image/png'
    assert any(record['media_type'] == 'application/zip' for record in saved['artifacts'].values())
    events = store.events(case['id'])
    assert any(event['type'] == 'hypothesis' and event.get('prior_result') for event in events)
    assert [event['seq'] for event in events] == list(range(1, len(events)+1))
    assert 'synthetic-test-only' not in json.dumps(saved)


async def test_runtime_browser_blocks_foreign_navigation_and_service_writes(tmp_path, live_server):
    browser = BrowserSession(live_server+'/', tmp_path)
    await browser.start()
    try:
        with pytest.raises(ValueError, match='configured demo'):
            await browser.execute(BrowserAction(action='open', url='https://example.com/'))
        result = await browser.page.evaluate("fetch('/api/reports',{method:'POST',body:'{}'}).then(()=> 'allowed').catch(()=> 'blocked')")
        assert result == 'blocked'
        result = await browser.execute(BrowserAction(action='inspect'))
        assert result['observation']['elements']
        assert result['evidence_id'].endswith('.png')
    finally:
        await browser.close()
