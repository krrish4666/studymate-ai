"""End-to-end auth flows with a persistent uvicorn server."""
import asyncio
import json
import subprocess
import sys
import time

import requests
import websockets

PORT = 18133
BASE = f'http://127.0.0.1:{PORT}'
CDP_PORT = 9227

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
   '.nav-actions .btn-ghost', '.nav-actions .btn-primary',
   '.nav-actions .btn-danger'].forEach(pick);
  out.__url = location.pathname;
  out.__bodyClass = document.body.className;
  out.__token = (localStorage.getItem('studymate-token') || '').slice(0, 12);
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

        # Register a real account through the API.
        EMAIL = 'test' + __import__('uuid').uuid4().hex[:8] + '@example.com'
        PASSWORD = 'hunter2pass'
        reg = requests.post(f'{BASE}/api/v1/auth/register',
                            json={'name': 'Grace Hopper', 'email': EMAIL,
                                  'password': PASSWORD}, timeout=20)
        print('register status:', reg.status_code)
        if reg.status_code == 201:
            token = reg.json().get('access_token', '')
            print('register token (prefix):', token[:18], '...')
            print('register user:', json.dumps(reg.json().get('user', {}))[:80])
        else:
            print('register body:', reg.text[:200])

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
                    return 'JS-ERROR: ' + str(r['exceptionDetails'])[:220]
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

            await navigate(BASE + '/')
            await evaluate("localStorage.clear();")
            await navigate(BASE + '/')
            print('===== 1. GUEST =====')
            await probe('guest landing')

            print('\n===== 2. LOGIN via form =====')
            await navigate(BASE + '/login')
            await evaluate(
                "document.getElementById('email').value='" + EMAIL + "';"
                "document.getElementById('password').value='" + PASSWORD + "';'filled'")
            await evaluate("document.querySelector('#login-form').requestSubmit();")
            for _ in range(40):
                await asyncio.sleep(0.25)
                url = await evaluate('location.pathname')
                if url == '/':
                    break
            await asyncio.sleep(1.5)
            await probe('after login submit')

            print('\n===== 3. RETURNING USER (reload keeps JWT) =====')
            await navigate(BASE + '/')
            await probe('returning user')

            print('\n===== 4. Profile link target =====')
            print('avatar href:', await evaluate("document.querySelector('.nav-account').href"))
            print('profile btn href:',
                  await evaluate("document.querySelector('.nav-actions .btn-ghost').href"))

            print('\n===== 5. LOGOUT =====')
            await evaluate("document.getElementById('logout-btn').click();")
            await asyncio.sleep(2.5)
            print('url after logout:', await evaluate('location.pathname'))
            print('token after logout:', await evaluate("localStorage.getItem('studymate-token')"))
            await probe('guest after logout')

            print('\n===== 6. OAUTH callback (?token=...) =====')
            payload = (
                'eyJhbGciOiJIUzI1NiJ9.'
                + __import__('base64').b64encode(json.dumps({
                    'sub': '42', 'name': 'Grace Oauth', 'email': 'g@o.com',
                    'image': ''}).encode()).decode().rstrip('=')
                + '.sig'
            )
            await navigate(BASE + '/login?token=' + payload)
            for _ in range(40):
                await asyncio.sleep(0.25)
                url = await evaluate('location.pathname')
                if url == '/':
                    break
            await asyncio.sleep(1.5)
            await probe('after oauth callback')

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
