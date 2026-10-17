"""Start the loopback demo; use the workspace browser cache when present."""
import argparse
import os
import webbrowser
import json
import urllib.request
import urllib.error

import uvicorn
from app.settings import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--open',action='store_true',help='Open the local store in your browser.')
    args=parser.parse_args()
    browsers=ROOT/'.local/browsers'
    if browsers.is_dir():
        os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(browsers))
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1) as response:
            existing=json.load(response)
        if existing.get('status')=='ok' and 'milestone' in existing and 'provider' in existing:
            print('Repro is already running at http://127.0.0.1:8000/')
            if args.open:
                webbrowser.open('http://127.0.0.1:8000/')
            return
    except (OSError,ValueError,urllib.error.URLError):
        pass
    if args.open:
        import threading
        threading.Timer(1,lambda:webbrowser.open('http://127.0.0.1:8000/')).start()
    uvicorn.run('app.main:app',host='127.0.0.1',port=8000)


if __name__=='__main__':
    main()
