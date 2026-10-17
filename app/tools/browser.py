"""A small browser tool surface. Models never provide JavaScript or selectors."""
import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from playwright.async_api import async_playwright
from pydantic import BaseModel, ConfigDict, Field


class BrowserAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['open', 'inspect', 'click', 'fill', 'select', 'back', 'capture', 'reset']
    element_id: str | None = Field(default=None, max_length=20)
    value: str | None = Field(default=None, max_length=1000)
    url: str | None = Field(default=None, max_length=2048)


class BrowserSession:
    def __init__(self, target_url, evidence_dir: Path, on_artifact=None):
        self.target_url = target_url
        parsed = urlsplit(target_url)
        self.origin = f'{parsed.scheme}://{parsed.netloc}'
        self.evidence_dir = Path(evidence_dir)
        self.on_artifact = on_artifact or (lambda path, media: Path(path).name)
        self.elements = {}
        self.replay = []
        self.counter = 0
        self.context_counter = 0
        self.console_errors = []
        self.context = None
        self.engine = None
        self.browser = None

    def allowed_url(self, value, navigation=False):
        try:
            parsed = urlsplit(value)
            if f'{parsed.scheme}://{parsed.netloc}' != self.origin or parsed.username or parsed.password:
                return False
            if parsed.query or parsed.fragment:
                return False
            if parsed.path in {'', '/', '/rules'}:
                return True
            return not navigation and parsed.path.startswith(('/static/', '/store-assets/')) and parsed.path.endswith(('.js', '.css', '.svg', '.png', '.woff2'))
        except ValueError:
            return False

    async def guard_request(self, route):
        request = route.request
        if request.method not in {'GET', 'HEAD'} or not self.allowed_url(request.url, request.is_navigation_request()):
            await route.abort('blockedbyclient')
        else:
            await route.continue_()

    async def start(self):
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.engine = await async_playwright().start()
        self.browser = await self.engine.chromium.launch()
        await self.reset()

    async def end_context(self):
        if self.context:
            context, self.context = self.context, None
            try:
                trace = self.evidence_dir / f'trace-{self.context_counter}.zip'
                await context.tracing.stop(path=trace)
                self.on_artifact(trace, 'application/zip')
            finally:
                await context.close()

    async def close(self):
        try:
            await self.end_context()
        finally:
            if self.browser:
                await self.browser.close()
            if self.engine:
                await self.engine.stop()

    async def reset(self):
        await self.end_context()
        self.context_counter += 1
        self.context = await self.browser.new_context(viewport={'width': 1360, 'height': 900},
                                                       service_workers='block', accept_downloads=False)
        await self.context.route('**/*', self.guard_request)
        await self.context.route_web_socket('**/*', lambda websocket: websocket.close())
        await self.context.tracing.start(screenshots=True, snapshots=True, sources=False)
        self.page = await self.context.new_page()
        self.page.set_default_timeout(5000)
        self.page.on('pageerror', lambda error: self.console_errors.append(str(error)[:300]))
        self.elements = {}
        self.replay = []
        self.console_errors = []
        await self.page.goto(self.target_url, wait_until='domcontentloaded')

    async def inspect(self):
        dialogs = await self.page.locator('dialog[open]').all()
        root = dialogs[-1] if dialogs else self.page.locator('body')
        text = (await root.inner_text())[:6000]
        self.elements = {}
        controls = []
        candidates = await root.locator('button,input,textarea,select,a,summary').all()
        for element in candidates[:80]:
            if not await element.is_visible():
                continue
            metadata = await element.evaluate('''el => ({
                tag:el.tagName.toLowerCase(), type:el.getAttribute('type'),
                name:el.getAttribute('aria-label') ||
                  (el.labels ? Array.from(el.labels).map(l=>l.textContent.trim()).join(' ') : '') ||
                  el.textContent.trim() || el.getAttribute('placeholder') || '',
                html_id:el.id || null,
                value:('value' in el && el.type!=='password') ? el.value : null,
                disabled:!!el.disabled
            })''')
            if metadata['type'] in {'hidden', 'password', 'file'}:
                continue
            metadata['name'] = ' '.join(metadata['name'].split())[:200]
            ref = f'e{len(controls) + 1}'
            self.elements[ref] = (element, metadata)
            controls.append({'id': ref, **metadata})
        return {'url': self.page.url, 'text': text, 'elements': controls,
                'console_errors': self.console_errors[-5:]}

    async def capture(self):
        self.counter += 1
        path = self.evidence_dir / f'screenshot-{self.counter:03d}.png'
        await self.page.screenshot(path=path, full_page=False)
        return self.on_artifact(path, 'image/png')

    async def execute(self, action: BrowserAction):
        record = {'action': action.action}
        if action.action == 'open':
            url = action.url or self.target_url
            if not self.allowed_url(url, navigation=True):
                raise ValueError('Only configured demo pages may be opened.')
            await self.page.goto(url, wait_until='domcontentloaded')
            record['url'] = url
        elif action.action == 'reset':
            await self.reset()
        elif action.action == 'back':
            await self.page.go_back(wait_until='domcontentloaded')
        elif action.action in {'click', 'fill', 'select'}:
            if action.element_id not in self.elements:
                raise ValueError('Unknown or stale element ID. Inspect the page again.')
            element, metadata = self.elements[action.element_id]
            record['target'] = {k: metadata[k] for k in ('tag', 'name', 'html_id')}
            if action.action == 'click':
                await element.click()
            elif action.action == 'fill':
                if metadata['tag'] not in {'input', 'textarea'} or action.value is None:
                    raise ValueError('Fill requires a visible text input and a value.')
                await element.fill(action.value)
                record['value'] = action.value
            else:
                if metadata['tag'] != 'select' or action.value is None:
                    raise ValueError('Select requires a visible select field and a value.')
                await element.select_option(action.value)
                record['value'] = action.value
        observation = await self.inspect()
        evidence_id = await self.capture()
        if action.action not in {'inspect', 'capture', 'reset'}:
            self.replay.append(record)
        return {'observation': observation, 'evidence_id': evidence_id,
                'executed_action': record, 'replay_steps': len(self.replay)}
