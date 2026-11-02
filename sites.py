# Targeted interaction on the crawl's customizable-select sites, whose selects are hidden at load
# (in a dialog or a collapsed nav): click the opener, click the select, click another option.
# Usage: .venv/bin/python -I sites.py OUT.json [SETUP ...]   (shots go to out/shots/sites-*)
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import scrub
from qa import FF_BIN, PREFS

HERE = os.path.dirname(os.path.abspath(__file__))
URLS = [l.strip() for l in open(os.path.join(HERE, 'pages-batch1.txt')) if l.strip() and not l.startswith('#')]
pick = lambda host: next(u for u in URLS if host in u)
TARGETS = [
    ('artheroes', pick('artheroes.com'), 1366, '.site-header__language-toggle', '#preferences-destination-url'),
    ('werkaandemuur', pick('werkaandemuur.nl'), 1366, '.site-header__language-toggle', '#preferences-destination-url'),
    # 500: Firefox's minimum viewport width; the nav collapses behind #menu-toggle below ~800.
    ('slangzone', pick('slangzone.net'), 500, '#menu-toggle', '#nav-lang-select'),
]
SHOTS = os.path.join(HERE, 'out', 'shots')

STATE = r"""
const s = document.querySelector(Q);
if (!s) return null;
const r = s.getBoundingClientRect(), sc = s.querySelector('selectedcontent');
let open = null; try { open = s.matches(':open'); } catch (e) { open = 'unsupported'; }
const opts = [...s.querySelectorAll('option')].map(o => { const q = o.getBoundingClientRect(); return [q.left, q.top, q.width, q.height].map(Math.round); });
return {
  app: getComputedStyle(s).appearance, rect: [r.left, r.top, r.width, r.height].map(Math.round),
  idx: s.selectedIndex, len: s.options.length, open,
  visibleOptions: opts.filter(o => o[2] && o[3]).length, opts,
  selectedcontentLen: sc ? sc.textContent.trim().length : null,
  selectedcontentMatches: sc && s.selectedOptions[0] ? sc.textContent.trim() === s.selectedOptions[0].textContent.trim() : null,
  path: location.pathname.length, events: (window.__ev || []).splice(0),
};
"""
# A consent dialog shown in some setups blocks the opener: find its accept button.
CONSENT = r"""
const re = /accept|agree|akkoord|accepteren|allow|alle|ok\b|no, thanks|nee, bedankt|consent|прийняти|погоджуюсь|згоден/i;
for (const dlg of document.querySelectorAll('dialog[open], .fc-consent-root, [class*=consent], [id*=consent], [class*=cookie], [id*=cookie]')) {
  if (!dlg.getBoundingClientRect().width) continue;
  const b = [...dlg.querySelectorAll('button, a[role=button]')].find(b => re.test(b.textContent) && b.getBoundingClientRect().width);
  if (b) { const r = b.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }
}
return null;
"""
LISTEN = r"""
window.__ev = [];
const s = document.querySelector(Q);
if (s) for (const e of ['change', 'input']) s.addEventListener(e, () => __ev.push(e));
"""


def center(rect):
    return rect[0] + rect[2] / 2, rect[1] + rect[3] / 2


def target_option(st):
    for i, o in enumerate(st['opts']):
        if o[2] and o[3] and i != st['idx'] and o[1] > 0:
            return i, o
    return None, None


async def chrome(setup):
    from playwright.async_api import async_playwright
    res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome-canary', headless=True)
        for name, url, w, opener, sel in TARGETS:
            steps = []
            pg = await (await b.new_context(viewport={'width': w, 'height': 800})).new_page()
            st = lambda: pg.evaluate(f'(Q) => {{ {STATE} }}', sel)
            try:
                await pg.goto(url, wait_until='load', timeout=30000)
            except Exception as e:
                steps.append(('load_error', type(e).__name__))
            await asyncio.sleep(4)
            await pg.evaluate(f'(Q) => {{ {LISTEN} }}', sel)
            for _ in range(3):
                cb = await pg.evaluate(f'() => {{ {CONSENT} }}')
                if not cb:
                    break
                await pg.mouse.click(*center(cb))
                await asyncio.sleep(1)
                steps.append(('dismissed consent', None))
            ob = await pg.evaluate('(q) => { const e = document.querySelector(q); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }', opener)
            if ob:
                await pg.mouse.click(*center(ob))
                await asyncio.sleep(1)
            steps.append(('open container', await st()))
            s0 = steps[-1][1]
            if s0 and s0['rect'][2]:
                await pg.mouse.click(*center(s0['rect']))
                await asyncio.sleep(1)
                steps.append(('click select', await st()))
                await pg.screenshot(path=os.path.join(SHOTS, f'sites-{name}-{setup}-open.png'))
                i, o = target_option(steps[-1][1])
                if o:
                    await pg.mouse.click(*center(o))
                    await asyncio.sleep(1)
                    try:
                        steps.append((f'click option {i}', await st()))
                    except Exception as e:  # navigated
                        steps.append((f'click option {i}', {'navigated': True}))
                    await pg.screenshot(path=os.path.join(SHOTS, f'sites-{name}-{setup}-picked.png'))
            res[name] = steps
            await pg.context.close()
        res['version'] = b.version
        await b.close()
    return res


def firefox(setup):
    from selenium import webdriver
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    o = Options()
    o.binary_location = FF_BIN
    o.add_argument('-headless')
    for pref in PREFS:
        o.set_preference(pref, setup == 'B')
    d = webdriver.Firefox(options=o, service=Service(log_output=os.devnull))
    d.set_page_load_timeout(30)
    res = {'version': d.capabilities.get('browserVersion')}

    def click(x, y):
        a = ActionChains(d)
        a.w3c_actions.pointer_action.move_to_location(int(x), int(y))
        a.w3c_actions.pointer_action.click()
        a.perform()

    for name, url, w, opener, sel in TARGETS:
        steps = []
        d.set_window_size(w, 800)
        iw, ih = d.execute_script('return [innerWidth, innerHeight]')
        d.set_window_size(w + w - iw, 800 + 800 - ih)
        st = lambda: d.execute_script('const Q = arguments[0];' + STATE, sel)
        try:
            d.get(url)
        except Exception as e:
            steps.append(('load_error', type(e).__name__))
        time.sleep(4)
        d.execute_script('const Q = arguments[0];' + LISTEN, sel)
        for _ in range(3):
            cb = d.execute_script(CONSENT)
            if not cb:
                break
            click(*center(cb))
            time.sleep(1)
            steps.append(('dismissed consent', None))
        ob = d.execute_script('const e = document.querySelector(arguments[0]); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height];', opener)
        if ob:
            click(*center(ob))
            time.sleep(1)
        steps.append(('open container', st()))
        s0 = steps[-1][1]
        if s0 and s0['rect'][2]:
            click(*center(s0['rect']))
            time.sleep(1)
            steps.append(('click select', st()))
            d.save_screenshot(os.path.join(SHOTS, f'sites-{name}-{setup}-open.png'))
            i, op = target_option(steps[-1][1])
            if op:
                click(*center(op))
                time.sleep(1)
                try:
                    steps.append((f'click option {i}', st()))
                except Exception:
                    steps.append((f'click option {i}', {'navigated': True}))
                d.save_screenshot(os.path.join(SHOTS, f'sites-{name}-{setup}-picked.png'))
        res[name] = steps
    d.quit()
    return res


if __name__ == '__main__':
    os.makedirs(SHOTS, exist_ok=True)
    out, setups = sys.argv[1], sys.argv[2:] or ['A', 'B', 'C']
    results = {s: asyncio.run(chrome(s)) if s.startswith('A') else firefox(s) for s in setups}
    json.dump(results, open(out, 'w'), indent=1)
