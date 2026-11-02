# Run the local test pages in every setup with real input (Playwright mouse/keyboard in Chrome,
# WebDriver actions in Firefox) and record window.state() after each step.
# Usage: .venv/bin/python -I local.py OUT.json [SETUP ...]   (serves tests/ on a local port)
# Steps: load; click the select; click its last option; reload; then the KEYS sequence.
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve
from qa import FF_BIN, PREFS

TESTS = sorted(f for f in os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests'))
               if f.startswith('t') and f.endswith('.html'))
PAUSE = 0.6
HEADFUL = os.environ.get('HEADFUL') == '1'
KEYS = ['Tab', 'ArrowDown', 'Enter', 'Escape', 'ArrowDown', 'ArrowDown', 'Enter', 'Tab', 'Space', 'ArrowUp', 'Space']


def center(rect):
    return rect[0] + rect[2] / 2, rect[1] + rect[3] / 2


async def chrome(base, setup):
    from playwright.async_api import async_playwright
    res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome-canary', headless=not HEADFUL)
        for t in TESTS:
            page = await (await b.new_context(viewport={'width': 800, 'height': 600})).new_page()
            steps = []
            st = lambda: page.evaluate('state()')
            await page.goto(base + t)
            steps.append(('load', await st()))
            await page.mouse.click(*center(steps[-1][1]['rect']))
            await asyncio.sleep(PAUSE)
            steps.append(('click select', await st()))
            last = steps[-1][1]['options'][-1]
            if last[2] and last[3]:
                await page.mouse.click(*center(last))
                await asyncio.sleep(PAUSE)
                steps.append(('click last option', await st()))
            await page.goto(base + t + '?k')
            for k in KEYS:
                await page.keyboard.press(k if k != 'Space' else ' ')
                await asyncio.sleep(PAUSE)
                steps.append((k, await st()))
            res[t] = steps
            await page.context.close()
        res['version'] = b.version
        await b.close()
    return res


def firefox(base, setup):
    from selenium import webdriver
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    o = Options()
    o.binary_location = FF_BIN
    if not HEADFUL:
        o.add_argument('-headless')
    for pref in PREFS:
        o.set_preference(pref, setup == 'B')
    d = webdriver.Firefox(options=o, service=Service(log_output=os.devnull))
    d.set_window_size(800, 600)
    # Make the viewport 800x600 like Chrome's, so coordinates line up.
    iw, ih = d.execute_script('return [innerWidth, innerHeight]')
    d.set_window_size(800 + 800 - iw, 600 + 600 - ih)
    st = lambda: d.execute_script('return state()')
    res = {'version': d.capabilities.get('browserVersion')}
    keys = {'Tab': Keys.TAB, 'ArrowDown': Keys.ARROW_DOWN, 'ArrowUp': Keys.ARROW_UP, 'Enter': Keys.ENTER,
            'Escape': Keys.ESCAPE, 'Space': Keys.SPACE}
    for t in TESTS:
        steps = []
        d.get(base + t)
        steps.append(('load', st()))
        x, y = center(steps[-1][1]['rect'])
        ActionChains(d).move_by_offset(0, 0).perform()
        a = ActionChains(d)
        a.w3c_actions.pointer_action.move_to_location(int(x), int(y))
        a.w3c_actions.pointer_action.click()
        a.perform()
        time.sleep(PAUSE)
        steps.append(('click select', st()))
        last = steps[-1][1]['options'][-1]
        if last[2] and last[3]:
            x, y = center(last)
            a = ActionChains(d)
            a.w3c_actions.pointer_action.move_to_location(int(x), int(y))
            a.w3c_actions.pointer_action.click()
            a.perform()
            time.sleep(PAUSE)
            steps.append(('click last option', st()))
        d.get(base + t + '?k')
        for k in KEYS:
            ActionChains(d).send_keys(keys[k]).perform()
            time.sleep(PAUSE)
            steps.append((k, st()))
        res[t] = steps
    d.quit()
    return res


if __name__ == '__main__':
    out = sys.argv[1]
    setups = sys.argv[2:] or ['A', 'B', 'C']
    base = serve(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests'))
    results = {}
    for s in setups:
        results[s] = asyncio.run(chrome(base, s)) if s.startswith('A') else firefox(base, s)
    json.dump(results, open(out, 'w'), indent=1, ensure_ascii=False)
