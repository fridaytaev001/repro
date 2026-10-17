"""Local, contained engineer handoff artifacts from actual case evidence."""
import hashlib
import json
import zipfile
from uuid import uuid4


def fixture_for(case):
    if not case.get('candidate') or not case.get('acceptance'):
        return None
    return {'schema_version': 1, 'target_id': 'demo-store',
            'fixture': 'fresh-context-v1; no server cart',
            'acceptance': case['acceptance'], 'candidate': case['candidate']}


def report_markdown(case):
    report = case['report']
    verification = case.get('verification') or {}
    rows = [f"# Repro case {case['id']}", '',
        f"Outcome: **{case.get('outcome') or case['stage']}**", '',
        f"Execution: {case.get('execution_mode', 'unavailable')}; model: {case.get('model') or 'none'}.", '',
        '## Complaint', '', report['complaint'], '', '## Expected behavior', '', report['expected_behavior'], '',
        '## Current result', '', case.get('message', ''), '',
        f"Investigation: {case.get('browser_action_count', 0)} actions, {case.get('provider_request_count', 0)} provider requests, {case.get('usage_tokens', 0)} budget/usage tokens.", '',
        '## Independent verification', '',
        f"Status: {verification.get('status', 'not run')}. {verification.get('reason', 'No independent conclusion is available.')}", '',
        f"Policy: {verification.get('policy', 'none')}; elapsed: {verification.get('elapsed_seconds', 'not measured')} seconds.", '',
        '## Actual candidate steps', '']
    for index, step in enumerate((case.get('candidate') or {}).get('steps', []), 1):
        rows.append(f"{index}. {json.dumps(step, ensure_ascii=False)}")
    if not case.get('candidate'):
        rows.append('Unavailable: no candidate was established.')
    rows += ['', '## Independent observed values', '']
    for row in verification.get('observations', []):
        rows.append(f"- Step {row['step']}: {json.dumps(row['values'], ensure_ascii=False)}; screenshot {row['evidence_id']}.")
    if case.get('repair'):
        repair = case['repair']
        rows += ['', '## Isolated repair', '',repair.get('message',''), '',
                 'The original demo remains the seeded baseline. A verified result applies only to the isolated copy.', '',
                 f"Diagnosis: {repair.get('cause','not established')}", '',
                 f"Baseline: {(repair.get('baseline') or {}).get('result',{}).get('regression','not measured')}; candidate: {(repair.get('candidate') or {}).get('result',{}).get('regression','not measured')}."]
    rows += ['', '## Limits', '',
        'A confirmed rule violation is not a source diagnosis or a verified repair. The registered verifier covers this demo’s coupon-preservation policy. No general claim of correctness is made.', '',
        'Reproduction test passes when it observes the defect. Regression test passes only when replay completes without that supported violation. Inconclusive replay fails both tests. See README.md in the bundle.', '']
    return '\n'.join(rows)


def test_source(regression=False):
    expected = 'fail' if regression else 'pass'
    name = 'regression_preserves_coupon' if regression else 'reproduces_documented_violation'
    return f'''"""Generated from saved steps; no model calls. See bundle README.md."""
import os
from pathlib import Path
import pytest
from scripts.replay_case import run_fixture

@pytest.mark.asyncio
@pytest.mark.browser
async def test_{name}(tmp_path):
    result = await run_fixture(Path(__file__).with_name('replay.json'),
        os.environ.get('REPRO_TARGET_URL', 'http://127.0.0.1:8000/'), tmp_path)
    assert result['status'] == '{expected}', result
'''


def build_handoff(store, case):
    directory = store.directory(case['id']) / 'exports' / str(uuid4())
    directory.mkdir(parents=True, exist_ok=True)
    entries = {'report.md': report_markdown(case).encode(),
               'report.json': json.dumps(case, indent=2, ensure_ascii=False).encode(),
               'events.jsonl': ''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in store.events(case['id'])).encode()}
    missing = []
    fixture = fixture_for(case)
    if fixture:
        entries.update({'replay.json': json.dumps(fixture, indent=2, ensure_ascii=False).encode(),
                        'test_reproduce.py': test_source().encode(),
                        'test_regression.py': test_source(True).encode()})
    else:
        missing.append('Replay and tests unavailable: no candidate with frozen criteria exists.')
    total = sum(map(len, entries.values()))
    # Export only previously registered evidence, never arbitrary filesystem paths
    # or previous handoff archives. Preserve originals and record omissions explicitly.
    for artifact_id, record in list(case.get('artifacts', {}).items()):
        if record['media_type'] not in {'image/png', 'application/zip','text/x-diff','application/json'} or 'exports' in record['file'].replace('\\', '/').split('/'):
            continue
        try:
            path, _ = store.artifact_path(case, artifact_id)
            size = path.stat().st_size
            if total + size > 64 * 1024 * 1024:
                missing.append(f'{artifact_id}: omitted to respect the 64 MiB bundle bound.')
                continue
            entries['evidence/'+artifact_id] = path.read_bytes()
            total += size
        except (FileNotFoundError, OSError):
            missing.append(f'{artifact_id}: registered evidence is unavailable.')
    readme = '''# Engineer handoff

Use a checkout of https://github.com/fridaytaev001/repro containing scripts/replay_case.py.
Install requirements-lock.txt and `python -m playwright install chromium`.
Start the synthetic target with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
Extract this ZIP into a directory inside the checkout (for example .local/handoff).

From the repository root, run:
  python -m scripts.replay_case .local/handoff/replay.json --expect reproduce
  python -m pytest .local/handoff/test_reproduce.py -q
  python -m pytest .local/handoff/test_regression.py -q

The reproduction test PASSES on the buggy target. The regression test FAILS on
that same target and must pass after a future repair. A replay/setup error is
inconclusive and cannot count as either proof. Both tests use fresh browsers.
Set REPRO_TARGET_URL for another loopback port. Exported replay uses no API key
or inference; start the app with a blank key if you only need browser replay.
The fixture has browser-local state and no server cart to namespace/reset.

report.json is a point-in-time snapshot. events.jsonl retains failed attempts
as well as later success. The manifest hashes every included file. No source
diagnosis, regression repair proof, or universal website correctness is claimed.
'''
    entries['README.md'] = readme.encode()
    manifest = {'case_id': case['id'], 'outcome': case.get('outcome'),
                'missing': missing, 'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                                             for name, data in entries.items()}}
    entries['manifest.json'] = json.dumps(manifest, indent=2).encode()
    for name in ('report.md', 'report.json'):
        (directory/name).write_bytes(entries[name])
    archive = directory/'handoff.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        for name, data in entries.items():
            output.writestr(name, data)
    return {kind: store.register(case, directory/name, media)
            for kind, name, media in [('markdown', 'report.md', 'text/markdown'),
                                     ('json', 'report.json', 'application/json'),
                                     ('bundle', 'handoff.zip', 'application/zip')]}
