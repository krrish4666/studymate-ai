"""Focused CDP test of the auth UI after the fix.

Simulates a returning user who already holds a JWT by seeding localStorage
BEFORE first navigation, then drives the real navigation + logout flow.
"""
import asyncio
import json
import subprocess
import sys
import time

import requests
import websockets

PORT = 18131
BASE = f'http://127.0.0.1:{PORT}'
CDP_PORT = 9225

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
      display: cs.display, visibility: cs.visibility, text:
        (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60),
      href: el.getAttribute('href') || '',
    };
  };
  ['.navbar', '.nav-links', '#auth-ui', '.nav-account',
   '.nav-actions .btn-ghost', '.nav-actions .btn-primary',
   '#logout-btn', '.mobile-menu-toggle'].forEach(pick);
  out.__url = location.pathname;
  out.__bodyClass = document.body.className;
  return JSON.stringify(out);
})()
'''


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

        events = []
        ident = [0]

        async with websockets.connect(page['webSocketDebuggerUrl'], max_size=10 ** 8) as ws:
            async def drain():
                while True:
                    try:
                        events.append(json.loads(await ws.recv()))
                    except Exception:
                        return

            drain_task = asyncio.create_task(drain())

            async def rpc(method, params=None):
                ident[0] += 1
                await ws.send(json.dumps({'id': ident[0], 'method': method,
                                          'params': params or {}}))
                for _ in range(400):
                    for e in list(events):
                        if e.get('id') == ident[0]:
                            return e
                    await asyncio.sleep(0.01)
                return {}

            async def evaluate(expr):
                res = await rpc('Runtime.evaluate',
                                {'expression': expr, 'returnByValue': True,
                                 'awaitPromise': True})
                r = res.get('result', {})
                if r.get('exceptionDetails'):
                    return 'JS-ERROR: ' + str(r['exceptionDetails'])[:200]
                return r.get('result', {}).get('value')

            async def wait_loaded():
                for _ in range(300):
                    v = await evaluate('document.readyState')
                    if v == 'complete':
                        return True
                    await asyncio.sleep(0.1)
                return False

            async def navigate(url):
                await rpc('Page.enable')
                await rpc('Page.navigate', {'url': url})
                await wait_loaded()
                await asyncio.sleep(1.5)

            async def probe(label):
                print(f'===== {label} =====')
                print(await evaluate(PROBE))

            # Seed first so JS module evaluation has it available on load.
            await navigate(BASE + '/about')
            await evaluate(
                "localStorage.setItem('studymate-token','x.y.z');"
                "localStorage.setItem('studymate-user', JSON.stringify("
                "{id:'1', name:'Add March', email:'ad@example.com', image:''}));"
            )

            # ---------- 1440 desktop ----------
            await rpc('Emulation.setDeviceMetricsOverride',
                      {'width': 1440, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
            await navigate(BASE + '/about')
            await probe('AUTH @1440 /about')

            # logout flow
            print('--- click logout ---')
            print(await evaluate(
                "document.getElementById('logout-btn').click(); 'clicked'"))
            await asyncio.sleep(1.5)
            print('url after logout:', await evaluate('location.pathname'))
            await probe('GUEST @1440 after logout')

            # ---------- 390 mobile ----------
            await rpc('Emulation.setDeviceMetricsOverride',
                      {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
            await navigate(BASE + '/about')
            await probe('GUEST @390 collapsed')
            # open the drawer so the guest actions are reachable
            print('drawer after toggle:',
                  await evaluate(
                      "document.querySelector('.mobile-menu-toggle').click();"
                      "document.getElementById('nav-menu').className"))
            await asyncio.sleep(0.4)
            await probe('GUEST @390 drawer open')

            # sign in as a returning user on mobile
            await evaluate(
                "localStorage.setItem('studymate-token','x.y.z');"
                "localStorage.setItem('studymate-user', JSON.stringify("
                "{id:'1', name:'Add March', email:'ad@example.com', image:''}));"
            )
            await navigate(BASE + '/about')
            await probe('AUTH @390 collapsed')
            print('drawer after toggle:',
                  await evaluate(
                      "document.querySelector('.mobile-menu-toggle').click();"
                      "document.getElementById('nav-menu').className"))
            await asyncio.sleep(0.4)
            await probe('AUTH @390 drawer open')

            drain_task.cancel()
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
