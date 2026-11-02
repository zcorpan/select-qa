# fallback.py's Firefox runs with layout.css.stretch-size-keyword.enabled added to PREFS (setup B+s).
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fallback
from harness import serve
fallback.PREFS.append('layout.css.stretch-size-keyword.enabled')
base = serve(os.path.join(fallback.HERE, 'tests'))
r = fallback.firefox(base, True)
json.dump({'B+stretch': r}, open(sys.argv[1], 'w'), indent=1)
for t in fallback.TESTS:
    p = r[t]['panel']
    print('B+stretch', t, r[t]['verdict'], p and {k: round(v) for k, v in p.items()})
