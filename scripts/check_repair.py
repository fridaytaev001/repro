"""Registered protected repair check, run in a sanitized child process."""
import argparse
import asyncio
import json
import threading
import tempfile
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scripts.replay_case import run_fixture
from app.tools.browser import BrowserSession, BrowserAction


async def controls(url, output):
    browser = BrowserSession(url, output/'controls')
    await browser.start()
    rows = []
    try:
        async def act(action, name=None, value=None):
            args = {'action':action}
            if name:
                observation = await browser.inspect()
                items = [e for e in observation['elements'] if e['name']==name or e.get('html_id')==name]
                if len(items)!=1:
                    raise ValueError('Control target missing or ambiguous.')
                args['element_id'] = items[0]['id']
            if value is not None:
                args['value'] = value
            return await browser.execute(BrowserAction(**args))
        async def total(expected):
            value = await browser.page.locator('#total').inner_text()
            if value != expected:
                raise AssertionError(f'Control expected {expected}, observed {value}.')
            rows.append({'expected':expected,'actual':value})
        await act('click','open-cart')
        await total('$100.00')
        await act('fill','coupon','VIP20')
        await act('click','Apply')
        if 'not eligible' not in await browser.page.locator('#coupon-message').inner_text():
            raise AssertionError('Guest eligibility control did not reject VIP20.')
        await total('$100.00')
        await act('fill','coupon','SAVE10')
        await act('click','Apply')
        await total('$90.00')
        await act('fill','coupon','VIP20')
        await act('click','Apply')
        await total('$90.00')
        await act('select','quantity','3')
        await total('$270.00')
        await act('click','continue-review')
        await total('$270.00')
        if await browser.page.locator('#coupon-form').is_visible():
            raise AssertionError('Coupon entry must remain hidden on review.')
        await act('click','reset-store')
        await total('$100.00')
        if browser.console_errors:
            raise AssertionError('Browser console errors occurred.')
        return {'status':'pass','values':rows}
    finally:
        await browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site',type=Path,required=True)
    parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    routes = {'/':'index.html','/rules':'rules.html','/store-assets/store.js':'store.js',
              '/static/style.css':'style.css','/static/report.js':'report.js'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass
        def do_GET(self):
            name = routes.get(self.path)
            if not name:
                self.send_error(404)
                return
            data = (args.site/name).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','application/javascript' if name.endswith('.js') else 'text/css' if name.endswith('.css') else 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(data)
    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    result = {'regression':'inconclusive','controls':{'status':'not_run'}}
    temporary = tempfile.TemporaryDirectory(prefix='repro-proof-')
    work = Path(temporary.name)
    try:
        replay = asyncio.run(run_fixture(args.fixture,url,work/'replay'))
        result['replay'] = replay
        if replay['status']=='inconclusive':
            return 2
        result['regression'] = 'fail' if replay['status']=='pass' else 'pass'
        result['controls'] = asyncio.run(controls(url,work))
        return 0 if result['regression']=='pass' else 1
    except Exception as error:
        result['error'] = type(error).__name__
        return 2
    finally:
        server.shutdown()
        server.server_close()
        with zipfile.ZipFile(args.output/'evidence.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for path in work.rglob('*'):
                if path.is_file():
                    archive.write(path,path.relative_to(work).as_posix())
        temporary.cleanup()
        (args.output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps({'regression':result['regression'],'controls':result['controls']['status'],
                          'error':result.get('error')}))


if __name__=='__main__':
    raise SystemExit(main())
