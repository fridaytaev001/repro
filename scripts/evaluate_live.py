"""Submit two labelled synthetic evaluation reports; summarize only saved facts.

No key is read here. The local worker owns real Crusoe requests. This script
does not fabricate hypotheses, outcomes, recovery, or cost measurements.
"""
import argparse
import json
from pathlib import Path

import httpx


def cost_estimate(case):
    # Published USD / million-token rate snapshot, checked 2026-10-17:
    # https://www.crusoe.ai/cloud/pricing (DeepSeek V4 Flash).
    if case.get('model') != 'deepseek-ai/Deepseek-V4-Flash':
        return None
    prompt = completion = cached = 0
    unknown_cache_calls = 0
    for call in case.get('calls', []):
        usage = call.get('usage') or {}
        if not all(isinstance(usage.get(k), int) and usage[k] >= 0 for k in ['prompt_tokens','completion_tokens']):
            return None
        details = usage.get('prompt_tokens_details') or {}
        count = details.get('cached_tokens')
        if count is None:
            unknown_cache_calls += 1
            count = 0
        if not isinstance(count, int) or not 0 <= count <= usage['prompt_tokens']:
            return None
        prompt += usage['prompt_tokens']
        completion += usage['completion_tokens']
        cached += count
    return {'usd_estimate': round(((prompt-cached)*.14 + cached*.03 + completion*.28)/1000000, 8),
        'prompt_tokens':prompt,'completion_tokens':completion,'cached_prompt_tokens':cached,
        'calls_with_unreported_cache':unknown_cache_calls,
        'basis':'Published 2026-10-17 rate snapshot; unknown cache charged at full input rate. Estimate, not invoice.',
        'source':'https://www.crusoe.ai/cloud/pricing'}

REPORTS = {
    'vip20_control': {'complaint': 'VIP20 will not apply to my guest bag. Is the checkout broken?',
        'expected_behavior': 'I expected VIP20 to take 20% off, but I may not be eligible.',
        'steps': 'Open the bag, enter VIP20, and press Apply.'},
    'recovery_attempt': {'complaint': 'My SAVE10 discount disappeared after I changed my address, but I cannot reproduce it with the steps I remember.',
        'expected_behavior': 'A valid SAVE10 coupon should survive address-only changes.',
        'steps': 'The sequence I remember is: open the bag, apply SAVE10, change the street address while still on the initial details step, then continue to review. Please try those remembered steps first; if they do not reproduce the problem, investigate alternatives.'}}


def summarize(case, events):
    calls = case.get('calls', [])
    return {'case_id': case['id'], 'execution_mode': case.get('execution_mode'),
        'model': case.get('model'), 'stage': case['stage'], 'outcome': case.get('outcome'),
        'stop_reason': case.get('stop_reason'), 'message': case.get('message'),
        'provider_requests': case.get('provider_request_count', 0),
        'browser_actions': case.get('browser_action_count', 0),
        'usage_tokens': case.get('usage_tokens', 0), 'elapsed_seconds': case.get('elapsed_seconds'),
        'hypotheses': case.get('hypotheses', []),
        'completion_response_ids': [c.get('response_id') for c in calls],
        'verification': {k: (case.get('verification') or {}).get(k) for k in ['id','status','action_count','elapsed_seconds','violations']},
        'replanning_events': [e for e in events if e['type']=='hypothesis' and e.get('prior_result')],
        'cost_estimate': cost_estimate(case)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8000')
    parser.add_argument('--submit', action='store_true')
    parser.add_argument('--manifest', type=Path, default=Path('.local/live-evaluation.json'))
    args = parser.parse_args()
    with httpx.Client(base_url=args.base, timeout=10) as client:
        if args.submit:
            cases = {}
            for label, report in REPORTS.items():
                response = client.post('/api/reports', json={**report, 'page_url':args.base+'/'})
                response.raise_for_status()
                cases[label] = response.json()['case_id']
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps(cases, indent=2), encoding='utf-8')
        cases = json.loads(args.manifest.read_text(encoding='utf-8'))
        results = {}
        for label, case_id in cases.items():
            response = client.get('/api/runs/'+case_id)
            response.raise_for_status()
            events = client.get('/api/runs/'+case_id+'/events').json()['events']
            results[label] = summarize(response.json(), events)
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
