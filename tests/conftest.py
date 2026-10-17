import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from app.main import create_app


@pytest.fixture(scope='session')
def live_server(tmp_path_factory):
    # Bind once and pass the open socket to avoid a port-selection race.
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    app = create_app(tmp_path_factory.mktemp('browser-cases'), {url}, enable_investigation=False)
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(.05)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
        raise RuntimeError('Test server did not start')
    yield url
    server.should_exit = True
    thread.join(timeout=5)
    sock.close()


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()
