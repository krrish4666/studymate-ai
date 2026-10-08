"""End-to-end auth flow test: real register -> login -> dashboard -> logout,
plus returning-JWT behaviour and the Google OAuth callback path."""
import asyncio
import json
import subprocess
import sys
import time

import requests
import websockets

PORT = 18132
BASE = f'http://127.0.0.1:{PORT}'
CDP_PORT = 9226

PROBE = r'''
(() => {
  const out = {};
  const pick = (sel) => {
    const el = document.querySelector(sel);
    if (!el) { out[sel] = 'MISSING'; return; }
    const r = el.getBoundingClientRect();
    out[sel] = {text: (el.textContent || '').replace(/\s+/g,' ').trim().slice(0,60),
                href: el.getAttribute('href') || '',
                w: Math.round(r.width), h: Math.round(r.height)};
  };
  ['.navbar', '#auth-ui', '.nav-account', '#logout-btn',
   '.nav-actions .btn-ghost', '.nav-actions .btn-danger'].forEach(pick);
  out.__url = location.pathname;
  out.__bodyClass = document.body.className;
  out.__token = localStorage.getItem('studymate-token');
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
                    return 'JS-ERROR: ' + str(r['exceptionDetails'])[:250]
                return r.get('result', {}).get('value')

            async def wait_loaded():
                for _ in range(300):
                    if await evaluate('document.readyState') == 'complete':
                        return True
                    await asyncio.sleep(0.1)
                return False

            async def navigate(url):
                await rpc('Page.enable')
                await rpc('Page.navigate', {'url': url})
                await wait_loaded()
                await asyncio.sleep(1.5)

            async def probe(label):
                print(f'----- {label} -----')
                print(await evaluate(PROBE))

            await rpc('Emulation.setDeviceMetricsOverride',
                      {'width': 1440, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})

            # 1. logged-out landing
            await evaluate('localStorage.clear();')
            await navigate(BASE + '/')
            print('1) GUEST landing')
            print(await evaluate(PROBE))

            # 2. real register through the form
            await navigate(BASE + '/register')
            await evaluate(
                "document.getElementById('name').value='Grace Hopper';"
                "document.getElementById('email').value='grace@example.com';"
                "document.getElementById('password').value='hunter2pass';"
                "'filled'")
            await evaluate("document.querySelector('#register-form').requestSubmit();")
            await asyncio.sleep(2.5)
            print('2) after REGISTER')
            print(await evaluate(PROBE))

            # 3. real login through the form
            await evaluate('localStorage.clear();')
            await navigate(BASE + '/login')
            await evaluate(
                "document.getElementById('email').value='grace@example.com';"
                "document.getElementById('password').value='hunter2pass';"
                "'filled'")
            await evaluate("document.querySelector('#login-form').requestSubmit();")
            await asyncio.sleep(2.5)
            print('3) after LOGIN')
            print(await evaluate(PROBE))

            # 4. returning user: reload with the stored token still present
            await navigate(BASE + '/')
            print('4) RETURNING USER (JWT persisted)')
            print(await evaluate(PROBE))

            # 5. profile link target
            print('5) profile href:',
                  await evaluate("document.querySelector('.nav-account').href"))

            # 6. logout
            await evaluate("document.getElementById('logout-btn').click();")
            await asyncio.sleep(2)
            print('6) after LOGOUT url:',
                  await evaluate('location.pathname'))
            print('   token:', await evaluate("localStorage.getItem('studymate-token')"))
            print('   after logout nav:')
            print(await evaluate(PROBE))

            # 7. OAuth callback: ?token= lands on /login
            await navigate(BASE + '/login?token=header.'
                          'eyJzdWIiOiI5IiwibmFtZSI6IkdyYWNlIiwiZW1haWwiOiJnQGUuY29tIiwiaW1hZ2UiOiIifQ=='
                          '.sig')
            await asyncio.sleep(2.5)
            print('7) after OAUTH CALLBACK')
            print(await evaluate(PROBE))

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
