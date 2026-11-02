# Open f5's picker in Firefox with PREFS on, wheel-scroll over it, and report which options are
# inside the viewport before and after. Usage: .venv/bin/python -I wheel_check.py [chrome]
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve
from qa import FF_BIN, PREFS
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
VIS = "const s = document.getElementById('trigger'); return [...s.options].filter(o => { const r = o.getBoundingClientRect(); return r.width && r.top >= 0 && r.bottom <= innerHeight; }).map(o => o.index)"
base = serve(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests'))
def firefox():
    o = Options(); o.binary_location = FF_BIN; o.add_argument('-headless')
    for p in PREFS: o.set_preference(p, True)
    d = webdriver.Firefox(options=o, service=Service(log_output=os.devnull)); d.set_window_size(800, 600)
    iw, ih = d.execute_script('return [innerWidth, innerHeight]'); d.set_window_size(1600 - iw, 1200 - ih)
    d.get(base + 'f5-select-fallback-tall.html')
    a = d.execute_script('const r = document.getElementById("trigger").getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]')
    ac = ActionChains(d); ac.w3c_actions.pointer_action.move_to_location(int(a[0]), int(a[1])); ac.w3c_actions.pointer_action.click(); ac.perform(); time.sleep(0.6)
    print('open', d.execute_script("return document.getElementById('trigger').matches(':open')"), 'options inside viewport', d.execute_script(VIS))
    first = d.execute_script("const r = document.getElementById('trigger').options[1].getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]")
    ActionChains(d).scroll_by_amount(0, 0).perform()
    from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
    ActionChains(d).scroll_from_origin(ScrollOrigin.from_viewport(int(first[0]), int(first[1])), 0, 600).perform(); time.sleep(0.6)
    print('after wheel: open', d.execute_script("return document.getElementById('trigger').matches(':open')"), 'options inside viewport', d.execute_script(VIS),
          'scrollY', d.execute_script('return scrollY'))
    d.quit()


# The same in Chrome Canary (run with argument "chrome").
def chrome():
    import asyncio
    from playwright.async_api import async_playwright
    async def main():
        async with async_playwright() as p:
            b = await p.chromium.launch(channel='chrome-canary')
            pg = await (await b.new_context(viewport={'width': 800, 'height': 600})).new_page()
            await pg.goto(base + 'f5-select-fallback-tall.html')
            js = '() => { ' + VIS + ' }'
            a = await pg.evaluate('() => { const r = document.getElementById("trigger").getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }')
            await pg.mouse.click(*a); await asyncio.sleep(0.6)
            v = await pg.evaluate(js)
            print('chrome', b.version, 'options inside viewport', v)
            o = await pg.evaluate(f'() => {{ const r = document.getElementById("trigger").options[{v[0]}].getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }}')
            await pg.mouse.move(*o); await pg.mouse.wheel(0, 2000); await asyncio.sleep(0.6)
            print('chrome after wheel: options inside viewport', await pg.evaluate(js))
            await b.close()
    asyncio.run(main())


if __name__ == '__main__':
    chrome() if sys.argv[1:] == ['chrome'] else firefox()
