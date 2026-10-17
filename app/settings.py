"""Read local operator settings without ever exporting credentials to the UI."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default='', repr=False)
    model: str = ''
    target_url: str = 'http://127.0.0.1:8000/'
    queue_size: int = 5
    max_actions: int = 30
    max_calls: int = 24
    max_tokens: int = 80000
    timeout_seconds: int = 300
    max_output_tokens: int = 4096

    @classmethod
    def read(cls):
        local = dotenv_values(ROOT / '.env', interpolate=False)

        def value(name, default=''):
            return (os.environ.get(name) or local.get(name) or default).strip()

        return cls(api_key=value('CRUSOE_API_KEY'), model=value('CRUSOE_MODEL'),
                   target_url=value('REPRO_TARGET_URL', 'http://127.0.0.1:8000/'))

    def validate_target(self):
        url = urlsplit(self.target_url)
        if url.scheme not in {'http', 'https'} or url.username or url.password or url.path not in {'', '/'}:
            raise ValueError('Target must be a configured demo-store origin.')
        if url.hostname not in {'127.0.0.1', 'localhost', '::1'} or url.query or url.fragment:
            raise ValueError('This milestone supports loopback demo targets only.')

    def public(self):
        return {'provider': 'Crusoe', 'configured': bool(self.api_key),
                'model': self.model or 'Discover Nemotron 3 Super from the live catalog',
                'execution_mode': 'live' if self.api_key else 'unavailable',
                'target_url': self.target_url}
