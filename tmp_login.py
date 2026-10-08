"""Debug the /login page form submission and return state."""
import asyncio
import json
import subprocess
import sys
import time

import requests
import websockets

PORT = 18134
BASE = f'http://127.0.0.1:{PORT}'
CDP_PORT = 9228


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

        import uuid
        EMAIL = 'test' + uuid.uuid4().hex[:8] + '@example.com'
        PASSWORD = 'hunter2pass'
        reg = requests.post(f'{BASE}/api/v1/auth/register',
                            json={'name': 'Grace Hopper', 'email': EMAIL,
                                  'password': PASSWORD}, timeout=20)
        print('register:', reg.status_code)

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
                    if await evaluate('document.readyState') == 'complete':
                        return True
                    await asyncio.sleep(0.1)
                return False

            async def navigate(url):
                await rpc('Page.enable')
                await rpc('Page.navigate', {'url': url})
                await wait_loaded()
                await asyncio.sleep(1.2)

            await navigate(BASE + '/login')
            print('on login page, modules loaded:')
            print(await evaluate(
                "typeof document.querySelector('#login-form') !== 'null'"))
            # check the inline script is present at all
            print('form present:', await evaluate(
                "!!document.getElementById('login-form')"))
            print('email field present:', await evaluate(
                "!!document.getElementById('email')"))
            print('error/message el:', await evaluate(
                "document.getElementById('error-message').textContent"))

            await evaluate(
                "document.getElementById('email').value='" + EMAIL + "';"
                "document.getElementById('password').value='" + PASSWORD + "';'set'")
            print('values set:',
                  await evaluate("document.getElementById('email').value"),
                  await evaluate("document.getElementById('password').value"))

            submit = await evaluate(
                "document.querySelector('#login-form').requestSubmit(); 'submitted'")
            print('submit result:', submit)
            await asyncio.sleep(4)
            print('url after submit:', await evaluate('location.pathname'))
            print('token:', await evaluate("localStorage.getItem('studymate-token')"))

            print('\nconsole/network errors:')
            for e in events:
                if 'exceptionThrown' in e:
                    print('  EXC:', str(e['exceptionThrown'])[:300])

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
