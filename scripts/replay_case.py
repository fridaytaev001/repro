"""Run an exported replay without credentials or model inference."""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from app.agents.verifier import Verifier
from app.runs import CaseStore
from app.settings import Settings


async def run_fixture(path, target_url, output_directory):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('schema_version') != 1 or payload.get('target_id') != 'demo-store':
        raise ValueError('Unsupported replay fixture.')
    case = {'id': str(uuid4()), 'stage': 'awaiting_verification', 'outcome': None,
            'acceptance': payload['acceptance'], 'candidate': payload['candidate']}
    # URL relocation applies only to the recorded demo root or rules, never to
    # arbitrary paths. All final URLs still pass the browser's loopback guard.
    from urllib.parse import urlsplit, urljoin
    Settings(target_url=target_url).validate_target()
    for step in case['candidate']['steps']:
        if step.get('action') == 'open' and step.get('url'):
            url = urlsplit(step['url'])
            if url.scheme not in {'http', 'https'} or url.hostname not in {'127.0.0.1', 'localhost', '::1'} or url.path not in {'', '/', '/rules'} or url.query or url.fragment or url.username or url.password:
                raise ValueError('Replay contains an unsupported target URL.')
            step['url'] = urljoin(target_url, url.path or '/')
    return await Verifier(CaseStore(output_directory), case, Settings(target_url=target_url)).run()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--target', default='http://127.0.0.1:8000/')
    parser.add_argument('--output', type=Path, default=Path('runs/replays'))
    parser.add_argument('--expect', choices=['reproduce', 'regression'], default='reproduce')
    args = parser.parse_args()
    result = asyncio.run(run_fixture(args.fixture, args.target, args.output))
    print(json.dumps(result, indent=2))
    if result['status'] == 'inconclusive':
        return 2
    return 0 if result['status'] == ('pass' if args.expect == 'reproduce' else 'fail') else 1


if __name__ == '__main__':
    raise SystemExit(main())
