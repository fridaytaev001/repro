"""Save a real local report/evidence bundle and a delivery hash manifest."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

import httpx


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',required=True)
    parser.add_argument('--base',default='http://127.0.0.1:8000')
    parser.add_argument('--output',type=Path,default=Path('.local/delivery'))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with httpx.Client(base_url=args.base,timeout=60) as client:
        case=client.get('/api/runs/'+args.case)
        case.raise_for_status()
        for kind,name in [('bundle','repro-evidence.zip'),('json','repro-report.json'),('markdown','repro-report.md')]:
            response=client.get('/api/runs/'+args.case+'/exports/'+kind)
            response.raise_for_status()
            (args.output/name).write_bytes(response.content)
    files={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
           for p in args.output.iterdir() if p.is_file() and p.name!='delivery-manifest.json'}
    (args.output/'delivery-manifest.json').write_text(json.dumps({
        'case_id':args.case,'outcome':case.json()['outcome'],
        'recording_label':'Recorded local walkthrough of actual saved proof; not a new live inference run.',
        'created_at':datetime.now(timezone.utc).isoformat(),'files':files},indent=2),encoding='utf-8')
    print('Delivery artifacts saved:',', '.join(files))


if __name__=='__main__':
    main()
