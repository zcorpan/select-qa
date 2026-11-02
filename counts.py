# Recompute every count the README and findings cite, from committed files.
# Usage: python3 counts.py
import json, os, subprocess, sys
H = os.path.dirname(os.path.abspath(__file__))
j = lambda p: json.load(open(os.path.join(H, p)))
rows = lambda p: [json.loads(l) for l in open(os.path.join(H, p))]

print('## Scan (scan/pages.jsonl)')
subprocess.run([sys.executable, os.path.join(H, 'scan', 'summarize.py')], check=True)
scan = rows('scan/pages.jsonl')
real = sorted({r['url'].split('/')[2] for r in scan if set(r['base_hits']) & {'<selectedcontent', '::picker(select)'}})
print('hosts with <selectedcontent> or ::picker(select):', real)

print('\n## Sample (pages-batch1.labels.json)')
lab = j('pages-batch1.labels.json')
from collections import Counter
print(len(lab), dict(Counter(l for l, _ in lab)))

print('\n## Batch 1 (out/b1-*.jsonl)')
for s in ('A', 'A2', 'B', 'C'):
    rs = rows(f'out/b1-{s}.jsonl')
    print(s, rs[0]['version'], 'visits', len(rs), 'load errors', sum(bool(r.get('load_error')) for r in rs),
          'collect errors', sum(bool(r.get('collect_error')) for r in rs), 'sessions lost', sum(bool(r.get('session_lost')) for r in rs))
b = rows('out/b1-B.jsonl')
bs = [r for r in b if any(x['app'] == 'base-select' for x in r.get('selects', []))]
print('B pages with a base-select select:', len(bs), '; of those with it visible at load:',
      sum(any(x['app'] == 'base-select' and x['w'] for x in r['selects']) for r in bs))
f = j('out/b1-flags.json')
print('flagged:', len(f['flags']), f['stats'])
for r in (1, 2):
    print(f'recheck {r} flagged:', len(j(f'out/rc{r}-flags.json')['flags']), [x['feature_errors'] for x in j(f'out/rc{r}-flags.json')['flags']])

print('\n## Sites (local-out/sites5.json for B/C, sites4.json for A)')
s4, s5 = j('local-out/sites4.json'), j('local-out/sites5.json')
for name in ('artheroes', 'werkaandemuur', 'slangzone'):
    for setup, src in (('A', s4), ('B', s5), ('C', s5)):
        last = [st for step, st in src[setup][name] if isinstance(st, dict)][-1]
        print(name, setup, [step for step, _ in src[setup][name]], 'open picker visibleOptions',
              max(st['visibleOptions'] for step, st in src[setup][name] if isinstance(st, dict) and 'visibleOptions' in st))

print('\n## Local tests (select verdicts use the union of option rects, which includes options scrolled out\n'
      '## of a capped picker; the wheel check is the reachability measure)')
fb, fs = j('local-out/fallback4.json'), j('local-out/fallback4-stretch.json')
for t in sorted(k for k in fb['A'] if k != 'version'):
    print(t, {s: fb[s][t]['verdict'] for s in 'ABC'}, 'B+stretch:', fs['B+stretch'][t]['verdict'])
for f in ('wheel-chrome.txt', 'wheel-firefox.txt'):
    print(f, open(os.path.join(H, 'local-out', f)).read().strip())
k = j('local-out/run2.json')
for t in ('t1-picker-flags.html', 't2-nested-selectedcontent.html'):
    for s in 'AB':
        steps = k[s][t]
        i = [n for n, _ in steps].index('ArrowDown')
        print(t, s, 'after ArrowDown active:', steps[i][1]['active'], 'open:', steps[i][1]['open'],
              '| after Enter open:', steps[i + 1][1]['open'], '| after Escape, ArrowDown, ArrowDown, Enter: idx',
              [st['idx'] for n, st in steps[i + 3:i + 6]], 'open', [st['open'] for n, st in steps[i + 3:i + 6]])
