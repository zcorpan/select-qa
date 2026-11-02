# <select> QA harness: visits pages in one setup and records the state of every <select>, how
# scripts used the select APIs (preload trace), JS errors and console errors/warnings.
# Usage: .venv/bin/python qa.py SETUP PAGES.txt OUT.jsonl [--shots DIR]
# Setups: A, A2 = Chrome Canary (reference, twice for noise); B = Firefox Nightly with PREFS on
# (candidate); C = Firefox Nightly default, PREFS off (control).
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import scrub

FF_BIN = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
# Candidate prefs, as in Gecko's wpt metadata for the-select-element/customizable-select.
PREFS = ['dom.select.customizable_select.enabled', 'layout.css.appearance-base.enabled']
SETUPS = {'A': 'chrome', 'A2': 'chrome', 'B': 'firefox-on', 'C': 'firefox-off'}
WIDTH, HEIGHT, WAIT = 1366, 768, 3

PRELOAD = r"""() => {
  if (window.__selTrace) return;
  const t = window.__selTrace = {calls: {}, events: {}};
  const bump = (o, k) => { o[k] = (o[k] || 0) + 1; };
  const P = HTMLSelectElement.prototype, O = HTMLOptionElement.prototype;
  const wrapGet = (proto, name, key) => {
    const d = Object.getOwnPropertyDescriptor(proto, name);
    if (!d) return;
    const nd = {configurable: true, enumerable: d.enumerable};
    if (d.get) nd.get = function () { bump(t.calls, key + '.get'); return d.get.call(this); };
    if (d.set) nd.set = function (v) { bump(t.calls, key + '.set'); return d.set.call(this, v); };
    if (d.value && typeof d.value === 'function') {
      nd.writable = true;
      nd.value = function (...a) { bump(t.calls, key + '()'); return d.value.apply(this, a); };
    }
    Object.defineProperty(proto, name, nd);
  };
  for (const n of ['value', 'selectedIndex', 'options', 'selectedOptions', 'length', 'add', 'remove',
                   'item', 'namedItem', 'showPicker', 'type', 'multiple'])
    wrapGet(P, n, 'select.' + n);
  for (const n of ['selected', 'defaultSelected', 'text', 'index'])
    wrapGet(O, n, 'option.' + n);
  for (const e of ['change', 'input', 'focus', 'mousedown', 'click'])
    addEventListener(e, ev => { if (ev.target instanceof HTMLSelectElement) bump(t.events, e); }, true);
  const ael = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (type, ...rest) {
    if (this instanceof HTMLSelectElement || this instanceof HTMLOptionElement) bump(t.calls, 'listen.' + type);
    return ael.call(this, type, ...rest);
  };
}"""

# Values and option text are hashed: country/region pickers default to the tester's location.
COLLECT = r"""
const h = s => { let x = 5381; for (const c of String(s)) x = ((x * 33) ^ c.codePointAt(0)) >>> 0; return x.toString(36); };
const sels = [...document.querySelectorAll('select')];
return {
  ready: document.readyState,
  trace: window.__selTrace ? JSON.parse(JSON.stringify(window.__selTrace)) : null,
  count: sels.length,
  selects: sels.slice(0, 60).map(s => {
    const r = s.getBoundingClientRect(), cs = getComputedStyle(s);
    const so = s.selectedOptions[0];
    return {
      len: s.options.length, idx: s.selectedIndex, value: h(s.value), text: so ? h(so.text) : null,
      multiple: s.multiple, size: s.size,
      x: Math.round(r.left), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height),
      app: cs.appearance, display: cs.display, visibility: cs.visibility,
      kids: [...s.children].map(c => c.localName).filter(n => n !== 'option' && n !== 'optgroup').slice(0, 10),
      deep: s.querySelectorAll('option').length,
      selectedcontent: !!s.querySelector('selectedcontent'),
      button: !!s.querySelector(':scope > button'),
    };
  }),
};
"""


def scrub_msg(s):
    return scrub(s)[:400] if s else s


def visit_firefox(driver, url, logs, shot):
    logs.clear()
    rec = {}
    t0 = time.time()
    try:
        driver.get(url)
    except Exception as e:
        rec['load_error'] = type(e).__name__
    time.sleep(WAIT)
    try:
        rec.update(driver.execute_script(COLLECT))
        if shot:
            driver.save_screenshot(shot)
    except Exception as e:
        rec['collect_error'] = scrub_msg(str(e).splitlines()[0] if str(e) else type(e).__name__)
    rec['errors'] = [scrub_msg(m) for k, m in logs if k == 'exception']
    rec['console'] = [f'{k}: {scrub_msg(m)}' for k, m in logs if k != 'exception']
    rec['secs'] = round(time.time() - t0, 1)
    return rec


def run_firefox(setup, urls, out, shots):
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service

    def start():
        o = Options()
        o.binary_location = FF_BIN
        o.enable_bidi = True
        o.add_argument('-headless')
        for pref in PREFS:
            o.set_preference(pref, setup == 'B')
        d = webdriver.Firefox(options=o, service=Service(log_output=os.devnull))
        d.set_window_size(WIDTH, HEIGHT)
        d.set_page_load_timeout(30)
        d.set_script_timeout(20)
        logs = []
        d.script.add_javascript_error_handler(lambda e: logs.append(('exception', getattr(e, 'text', str(e)))))
        d.script.add_console_message_handler(
            lambda e: logs.append((getattr(e, 'level', ''), getattr(e, 'text', str(e))))
            if getattr(e, 'level', '') in ('error', 'warn', 'warning') else None)
        d.script.pin(PRELOAD)
        version = d.capabilities.get('browserVersion')
        pref = d.execute_script('return 1')  # session alive
        return d, logs, version

    d, logs, version = start()
    for i, url in enumerate(urls):
        rec = {'url': scrub(url), 'setup': setup, 'version': version}
        try:
            rec.update(visit_firefox(d, url, logs, shots and os.path.join(shots, f'{setup}-{i:04d}.png')))
        except Exception as e:  # lost session: maybe a crashed content process
            rec['session_lost'] = type(e).__name__
            try:
                d.quit()
            except Exception:
                pass
            d, logs, version = start()
        out.write(json.dumps(rec) + '\n')
        out.flush()
    d.quit()


async def run_chrome(setup, urls, out, shots):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome-canary', headless=True)
        for i, url in enumerate(urls):
            rec = {'url': scrub(url), 'setup': setup, 'version': b.version}
            logs = []
            ctx = await b.new_context(viewport={'width': WIDTH, 'height': HEIGHT})
            await ctx.add_init_script(f'({PRELOAD})()')
            page = await ctx.new_page()
            page.on('pageerror', lambda e: logs.append(('exception', str(e).splitlines()[0] if str(e) else '')))
            page.on('console', lambda m: logs.append((m.type, m.text)) if m.type in ('error', 'warning') else None)
            t0 = time.time()

            async def go():
                try:
                    await page.goto(url, timeout=30000, wait_until='load')
                except Exception as e:
                    rec['load_error'] = type(e).__name__
                await asyncio.sleep(WAIT)
                rec.update(await page.evaluate(f'() => {{ {COLLECT} }}'))
                if shots:
                    await page.screenshot(path=os.path.join(shots, f'{setup}-{i:04d}.png'))
            try:
                await asyncio.wait_for(go(), 60)
            except Exception as e:
                rec['collect_error'] = type(e).__name__
            rec['errors'] = [scrub_msg(m) for k, m in logs if k == 'exception']
            rec['console'] = [f'{k}: {scrub_msg(m)}' for k, m in logs if k != 'exception']
            rec['secs'] = round(time.time() - t0, 1)
            try:
                await asyncio.wait_for(ctx.close(), 15)
            except Exception:
                pass
            out.write(json.dumps(rec) + '\n')
            out.flush()
        await b.close()


if __name__ == '__main__':
    setup, pages, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    shots = sys.argv[5] if len(sys.argv) > 5 and sys.argv[4] == '--shots' else None
    if shots:
        os.makedirs(shots, exist_ok=True)
    urls = [l.strip() for l in open(pages) if l.strip() and not l.startswith('#')]
    with open(outp, 'w') as out:
        if SETUPS[setup] == 'chrome':
            asyncio.run(run_chrome(setup, urls, out, shots))
        else:
            run_firefox(setup, urls, out, shots)
