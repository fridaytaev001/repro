"""Atomic case snapshots and append-only, bounded per-case event records."""
import json
import os
import tempfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


def now():
    return datetime.now(timezone.utc).isoformat()


class CaseStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def directory(self, case_id):
        return self.root / str(UUID(str(case_id)))

    def save(self, case):
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root,
                                             suffix='.tmp', delete=False) as file:
                temporary = Path(file.name)
                json.dump(case, file, ensure_ascii=False, indent=2)
            os.replace(temporary, self.root / f"{UUID(case['id'])}.json")
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def read(self, case_id):
        return json.loads((self.root / f'{UUID(str(case_id))}.json').read_text(encoding='utf-8'))

    def event(self, case, event_type, summary, **data):
        sequence = case.get('event_count', 0) + 1
        event = {'seq': sequence, 'timestamp': now(), 'type': event_type,
                 'summary': summary, **data}
        directory = self.directory(case['id'])
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / 'events.jsonl').open('a', encoding='utf-8') as file:
            file.write(json.dumps(event, ensure_ascii=False) + '\n')
        case['event_count'] = sequence
        case['updated_at'] = event['timestamp']
        self.save(case)
        return event

    def events(self, case_id, after=0):
        path = self.directory(case_id) / 'events.jsonl'
        if not path.exists():
            return []
        return [event for line in path.read_text(encoding='utf-8').splitlines()
                if (event := json.loads(line))['seq'] > after]

    def register(self, case, path, media_type):
        directory = self.directory(case['id']).resolve()
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(directory):
            raise ValueError('Artifact escaped the case directory.')
        artifact_id = hashlib.sha256(str(resolved.relative_to(directory)).encode()).hexdigest()[:16] + resolved.suffix
        artifact = {'id': artifact_id, 'file': str(resolved.relative_to(directory)),
                    'media_type': media_type}
        case.setdefault('artifacts', {})[artifact_id] = artifact
        self.save(case)
        return artifact_id

    def artifact_path(self, case, artifact_id):
        record = case.get('artifacts', {}).get(artifact_id)
        if not record:
            raise FileNotFoundError(artifact_id)
        directory = self.directory(case['id']).resolve()
        path = (directory / record['file']).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise FileNotFoundError(artifact_id)
        return path, record['media_type']
