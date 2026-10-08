"""Definitive navbar check: real navigation, console/exception capture, and
computed geometry in guest + authenticated states at desktop and mobile."""
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import requests
import websockets

PORT = 18130
BASE = f'http://127.0.0.1:{PORT}'
CDP_PORT = 9224

NAVBAR = '.navbar, .nav-menu, .nav-links, #auth-ui'

PROBE = r'''
(() => {
  const out = {};
  const pick = (sel) => {
    const el = document.querySelector(sel);
    if (!el) { out[sel] = 'MISSING'; return; }
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    out[sel] = {
      rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
      display: cs.display, visibility: cs.visibility, opacity: cs.opacity,
      text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60),
    };
  };
  ['.navbar', '.nav-menu', '.nav-links', '#auth-ui',
   '.profile-link', '#logout-btn', '.mobile-menu-toggle',
   '.nav-actions .btn-ghost', '.nav-actions .btn-primary',
   '.nav-account', '.nav-actions .btn-secondary'].forEach(pick);
  out.__url = location.pathname;
  out.__bodyClass = document.body.className;
  out.__token = localStorage.getItem('studymate-token');
  out.__readyState = document.readyState;
  return JSON.stringify(out);
})()
'''

SEED = (
    "localStorage.setItem('studymate-token','x.y.z');"
    "localStorage.setItem('studymate-user', JSON.stringify("
    "{id:'1', name:'Add March', email:'ad@example.com', image:''}));"
)


async def main():
    server = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app.main:app',
         '--host', '127.0.0.1', '--port', str(PORT), '--log-level', 'warning'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd='.',
    )
    chrome = None
    try:
        for _ in range(120):
            try:
                if requests.get(f'{BASE}/health', timeout=1).status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)

        chrome = subprocess.Popen(
            [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
             '--headless=new', '--disable-gpu', '--no-sandbox',
             f'--remote-debugging-port={CDP_PORT}',
             '--window-size=1440,900', '--hide-scrollbars', 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        page = None
        for _ in range(120):
            try:
                targets = requests.get(f'http://127.0.0.1:{CDP_PORT}/json', timeout=1).json()
                page = next((t for t in targets if t.get('type') == 'page'), None)
                if page:
                    break
            except Exception:
                time.sleep(0.25)
        if not page:
            print('NO CDP PAGE TARGET')
            return

        events = []
        ident = [0]

        async with websockets.connect(page['webSocketDebuggerUrl'], max_size=10 ** 8) as ws:
            async def drain():
                while True:
                    try:
                        events.append(json.loads(await ws.recv()))
                    except Exception:
                        break

            task = asyncio.create_task(drain())

            async def rpc(method, params=None):
                ident[0] += 1
                await ws.send(json.dumps({'id': ident[0], 'method': method,
                                          'params': params or {}}))
                for _ in range(400):
                    await asyncio.sleep(0.01)
                    for e in events:
                        if e.get('id') == ident[0]:
                            return e
                return {}

            async def wait_loaded():
                for _ in range(300):
                    res = await rpc('Runtime.evaluate',
                                    {'expression': 'document.readyState',
                                     'returnByValue': True})
                    val = res.get('result', {}).get('result', {}).get('value')
                    if val == 'complete':
                        return True
                    await asyncio.sleep(0.1)
                return False

            async def navigate(url):
                await rpc('Page.enable')
                await rpc('Page.navigate', {'url': url})
                await wait_loaded()
                await asyncio.sleep(1.5)

            async def probe():
                res = await rpc('Runtime.evaluate',
                                {'expression': PROBE, 'returnByValue': True})
                return res.get('result', {}).get('result', {}).get('value')

            async def set_viewport(w, h):
                await rpc('Emulation.setDeviceMetricsOverride',
                          {'width': w, 'height': h, 'deviceScaleFactor': 1,
                           'mobile': w < 768})

            async def evaluate(expr):
                res = await rpc('Runtime.evaluate',
                                {'expression': expr, 'returnByValue': True})
                r = res.get('result', {})
                if r.get('exceptionDetails'):
                    return 'JS-ERROR: ' + json.dumps(r['exceptionDetails'])[:300]
                return r.get('result', {}).get('value')

            # ---- desktop 1440 guest ----
            await set_viewport(1440, 900)
            await navigate(BASE + '/')
            print('===== GUEST @1440 =====')
            print(await probe())

            # ---- desktop 1440 authenticated ----
            await evaluate(SEED)
            await navigate(BASE + '/')
            print('===== AUTH @1440 =====')
            print(await probe())

            # ---- mobile 390 guest ----
            await set_viewport(390, 844)
            await evaluate("localStorage.clear();")
            await navigate(BASE + '/')
            print('===== GUEST @390 =====')
            print(await probe())
            print('drawer open? ', await evaluate(
                "document.getElementById('nav-menu').className"))

            # ---- mobile 390 authenticated, drawer ----
            await evaluate(SEED)
            await navigate(BASE + '/')
            print('===== AUTH @390 =====')
            print(await probe())
            print('drawer open? ', await evaluate(
                "document.getElementById('nav-menu').className"))

            task.cancel()
    finally:
        if chrome:
            chrome.terminate()
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:
            server.kill()


if __name__ == '__main__':
    asyncio.run(main())
