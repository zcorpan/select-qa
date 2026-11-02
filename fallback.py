# Click #trigger in tests/f*.html and report where the picker/popover ends up relative to the
# viewport. Usage: .venv/bin/python -I fallback.py OUT.json [SETUP ...]
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve
from qa import FF_BIN, PREFS
HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = sorted(f for f in os.listdir(os.path.join(HERE, 'tests')) if f.startswith('f') and f.endswith('.html'))
W, H = 800, 600


def verdict(m):
    p = m['panel']
    if not p:
        return 'no panel'
    inside = p['left'] >= -0.5 and p['top'] >= -0.5 and p['right'] <= m['vw'] + 0.5 and p['bottom'] <= m['vh'] + 0.5
    above = p['bottom'] <= m['anchor']['top'] + 0.5
    return ('inside viewport' if inside else 'overflows viewport') + (', above anchor' if above else ', below anchor')


async def chrome(base):
    from playwright.async_api import async_playwright
    out = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome-canary')
        for t in TESTS:
            pg = await (await b.new_context(viewport={'width': W, 'height': H})).new_page()
            await pg.goto(base + t)
            a = await pg.evaluate('measure()')
            await pg.mouse.click(a['anchor']['x'] + a['anchor']['width'] / 2, a['anchor']['y'] + a['anchor']['height'] / 2)
            await asyncio.sleep(0.6)
            m = await pg.evaluate('measure()')
            out[t] = {'verdict': verdict(m), **m}
            await pg.screenshot(path=os.path.join(HERE, 'out', 'shots', f'fallback-A-{t}.png'))
            await pg.context.close()
        out['version'] = b.version
        await b.close()
    return out


def firefox(base, on):
    from selenium import webdriver
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    o = Options(); o.binary_location = FF_BIN; o.add_argument('-headless')
    for pref in PREFS:
        o.set_preference(pref, on)
    d = webdriver.Firefox(options=o, service=Service(log_output=os.devnull))
    d.set_window_size(W, H)
    iw, ih = d.execute_script('return [innerWidth, innerHeight]')
    d.set_window_size(W + W - iw, H + H - ih)
    out = {'version': d.capabilities.get('browserVersion')}
    for t in TESTS:
        d.get(base + t)
        a = d.execute_script('return measure()')['anchor']
        ac = ActionChains(d)
        ac.w3c_actions.pointer_action.move_to_location(int(a['x'] + a['width'] / 2), int(a['y'] + a['height'] / 2))
        ac.w3c_actions.pointer_action.click()
        ac.perform()
        time.sleep(0.6)
        m = d.execute_script('return measure()')
        out[t] = {'verdict': verdict(m), **m}
        d.save_screenshot(os.path.join(HERE, 'out', 'shots', f'fallback-{"B" if on else "C"}-{t}.png'))
    d.quit()
    return out


if __name__ == '__main__':
    base = serve(os.path.join(HERE, 'tests'))
    setups = sys.argv[2:] or ['A', 'B', 'C']
    res = {s: asyncio.run(chrome(base)) if s.startswith('A') else firefox(base, s == 'B') for s in setups}
    json.dump(res, open(sys.argv[1], 'w'), indent=1)
    for s, r in res.items():
        for t in TESTS:
            p = r[t]['panel']
            print(s, r['version'], t, r[t]['open'], r[t]['verdict'], p and {k: round(v) for k, v in p.items()})
