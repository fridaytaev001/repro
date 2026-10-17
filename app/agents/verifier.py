"""Independent replay and deterministic policy checks for the versioned demo.

No inference, source inspection, model-generated assertions, or shared browser
storage. Unsupported policies and replay failures are inconclusive, never proof.
"""
import asyncio
import hashlib
import json
import re
import time
from uuid import uuid4

from app.tools.browser import BrowserAction, BrowserSession


def acceptance_hash(acceptance):
    payload = {key: acceptance[key] for key in ('checks', 'assumptions')}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def money(text):
    match = re.fullmatch(r'\s*[−-]?\$([\d,]+\.\d{2})\s*', text)
    if not match:
        raise ValueError('Unrecognized visible currency value.')
    return int(match[1].replace(',', '').replace('.', ''))


class Verifier:
    def __init__(self, store, case, settings, browser_factory=BrowserSession):
        self.store, self.case, self.settings = store, case, settings
        self.browser_factory = browser_factory

    def event(self, kind, summary, **data):
        self.store.event(self.case, kind, summary, **data)

    def validate(self):
        acceptance = self.case.get('acceptance') or {}
        candidate = self.case.get('candidate') or {}
        if (acceptance.get('version') != 1 or not acceptance.get('checks')
                or acceptance_hash(acceptance) != acceptance.get('hash')
                or candidate.get('acceptance_hash') != acceptance.get('hash')
                or candidate.get('acceptance_version') != acceptance.get('version')):
            raise ValueError('Candidate criteria are missing or changed; investigate again.')
        if any(c.get('rule_source') != 'store-rules:v1' for c in acceptance['checks']):
            raise ValueError('Unsupported rule version; no verifier policy is registered.')
        steps = candidate.get('steps')
        if not isinstance(steps, list) or not 1 <= len(steps) <= self.settings.max_actions:
            raise ValueError('Candidate replay exceeds the verification action limit or is empty.')
        return steps

    async def values(self, browser):
        # Registered read-only DOM adapter for this demo. No internal cart/source access.
        return await browser.page.evaluate('''() => {
          const visible = el => !!el && !!el.getClientRects().length;
          const read = id => {const el=document.getElementById(id); return visible(el) ? el.textContent.trim() : null;};
          return {total:read('total'), subtotal:read('subtotal'), discount:read('discount'),
            coupon:read('coupon-label'), quantity:document.getElementById('quantity')?.value,
            coupon_message:read('coupon-message'),
            discount_visible:visible(document.getElementById('discount-row')),
            stage:visible(document.getElementById('review-panel'))?'review':
              visible(document.getElementById('address-form'))?'details':'other'};
        }''')

    async def replay_action(self, browser, step):
        if set(step) - {'action', 'target', 'value', 'url'}:
            raise ValueError('Unsupported replay fields.')
        action = step.get('action')
        if action not in {'open', 'back', 'click', 'fill', 'select'}:
            raise ValueError('Unsupported replay action.')
        arguments = {'action': action}
        if action == 'open':
            arguments['url'] = step.get('url')
        if action in {'click', 'fill', 'select'}:
            target = step.get('target') or {}
            observation = await browser.inspect()
            def matches(item):
                if item['tag'] != target.get('tag'):
                    return False
                if target.get('html_id'):
                    return item.get('html_id') == target['html_id']
                return item['name'] == target.get('name')
            controls = [item for item in observation['elements'] if matches(item)]
            if len(controls) != 1 or controls[0]['disabled']:
                raise ValueError('Replay target is missing, ambiguous, or disabled.')
            arguments['element_id'] = controls[0]['id']
            if action in {'fill', 'select'}:
                arguments['value'] = step.get('value')
        return await browser.execute(BrowserAction.model_validate(arguments))

    async def run(self):
        started = time.monotonic()
        self.settings.validate_target()
        self.case.update(stage='verifying', outcome=None,
                         message='Replaying candidate in a fresh browser context.')
        result = {'id': str(uuid4()), 'policy': 'store-rules:v1/coupon-preservation',
                  'status': 'inconclusive', 'observations': [], 'violations': [],
                  'criteria_hash': (self.case.get('acceptance') or {}).get('hash'),
                  'fixture': 'fresh-context-v1; browser-local cart; no server cart',
                  'execution_mode': 'real_browser', 'action_count': 0}
        self.case['verification'] = result
        self.event('verification_started', self.case['message'])
        browser = None
        try:
            steps = self.validate()
            directory = self.store.directory(self.case['id']) / result['id'] / 'verification'
            def artifact(path, media):
                return self.store.register(self.case, path, media)
            browser = self.browser_factory(self.settings.target_url, directory, on_artifact=artifact)
            async with asyncio.timeout(self.settings.verification_timeout_seconds):
                await browser.start()
                # A new context is the documented server-independent fixture. Check it
                # before replay so contaminated sessions cannot establish confirmation.
                fixture = await browser.page.evaluate("() => ({local:localStorage.length,session:sessionStorage.length,cookies:document.cookie})")
                # The target renders/persists its default cart immediately; validate its
                # visible baseline after opening the cart, never inspect that stored cart.
                result['initial_session_storage_empty'] = fixture['session'] == 0
                result['initial_cookies_empty'] = not fixture['cookies']
                if fixture['session'] or fixture['cookies']:
                    raise ValueError('Fresh-context fixture unexpectedly contains session data.')
                coupon_active = False
                baseline_checked = False
                for index, step in enumerate(steps):
                    if result['action_count'] >= self.settings.max_actions:
                        raise ValueError('Verification action limit reached.')
                    observed = await self.replay_action(browser, step)
                    result['action_count'] += 1
                    values = await self.values(browser)
                    row = {'step': index + 1, 'action': observed['executed_action'],
                           'values': values, 'evidence_id': observed['evidence_id']}
                    result['observations'].append(row)
                    self.event('verification_action', f'Independent replay step {index + 1}.', result=observed, values=values)
                    if values['total'] is None:
                        continue
                    total, subtotal = money(values['total']), money(values['subtotal'])
                    if not baseline_checked:
                        if (total != 10000 or subtotal != 10000 or values['discount_visible']
                                or values['quantity'] != '1' or values['stage'] != 'details'):
                            raise ValueError('The declared clean baseline was not observed.')
                        baseline_checked = True
                    # Only an actual DOM-observed successful SAVE10 application arms
                    # the persistence check. Coupon text in a model claim cannot do so.
                    if (values['coupon'] == 'SAVE10' and values['discount_visible']
                            and money(values['discount']) == subtotal // 10
                            and total == subtotal * 9 // 10):
                        coupon_active = True
                    target = step.get('target') or {}
                    if (step['action'] == 'open' or (step['action'] == 'click'
                            and target.get('html_id') in {'reset-store', 'finish-order'})):
                        coupon_active = False
                    if coupon_active and (values['coupon'] != 'SAVE10'
                            or not values['discount_visible'] or total != subtotal * 9 // 10):
                        result['violations'].append({'rule': 'SAVE10 preservation', 'step': index + 1,
                            'expected_total_cents': subtotal * 9 // 10,
                            'actual_total_cents': total, 'evidence_id': observed['evidence_id']})
                if not baseline_checked:
                    raise ValueError('Replay never exposed the declared clean checkout fixture.')
                result['status'] = 'pass' if result['violations'] else 'fail'
                result['reason'] = ('A documented coupon-preservation rule violation was independently observed.'
                                    if result['violations'] else 'Replay completed without a supported documented-rule violation.')
        except asyncio.CancelledError:
            result['reason'] = 'Verification cancelled or interrupted; no confirmation established.'
            raise
        except (ValueError, KeyError, TypeError, TimeoutError) as error:
            result['reason'] = ((str(error) or 'Verification time limit reached; no confirmation established.')
                                if isinstance(error, (ValueError, TimeoutError)) else 'Malformed candidate replay.')
        except Exception as error:
            result['reason'] = f'Independent replay blocked by {type(error).__name__}; no confirmation established.'
        finally:
            result['elapsed_seconds'] = round(time.monotonic() - started, 2)
            if browser:
                await browser.close()
            self.store.save(self.case)
        confirmed = result['status'] == 'pass'
        self.case.update(stage='finished', outcome='confirmed' if confirmed else 'blocked' if result['status'] == 'inconclusive' else 'not_reproduced',
                         stop_reason='independent_rule_violation' if confirmed else 'verification_' + result['status'],
                         message=result['reason'])
        self.event('verification_finished', result['reason'], verification_status=result['status'])
        return result
