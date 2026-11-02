# Compare setups per page and flag differences. Usage: python3 analyze_qa.py out/b1 [> flags.json]
# Reads PREFIX-{A,A2,B,C}.jsonl. Flags:
#   feature: B (candidate) differs from C (control, same engine with the prefs off);
#   vs-ref:  B differs from A where C agrees with A and A agrees with A2 (not page noise);
#   base:    a select with base-select appearance in A whose B state or size is far off.
import collections, json, re, sys

prefix = sys.argv[1]
KEYS = ('len', 'idx', 'value', 'text', 'deep', 'multiple', 'app', 'display')
PX = 3  # layout tolerance within one engine


def load(s):
    try:
        return {r['url']: r for r in map(json.loads, open(f'{prefix}-{s}.jsonl'))}
    except FileNotFoundError:
        return {}


R = {s: load(s) for s in ('A', 'A2', 'B', 'C')}


def norm(m):
    m = re.sub(r'https?://\S+', '<url>', m or '')
    m = re.sub(r'[\w-]*[0-9][\w-]*', 'N', m)
    return m[:200]


def sel_diff(x, y, layout=True, expect_base=False):
    """Differences between two select lists (aligned by document order). With expect_base, y is the
    candidate and x the control: appearance, display and size of selects that have base-select
    appearance in y are expected to differ, so only their state is compared."""
    if not x.get('selects') and not y.get('selects'):
        return []
    if x.get('count') != y.get('count'):
        return [f"count {x.get('count')} vs {y.get('count')}"]
    out = []
    for i, (a, b) in enumerate(zip(x['selects'], y['selects'])):
        base = expect_base and b.get('app') == 'base-select'
        for k in KEYS:
            if base and k in ('app', 'display'):
                continue
            if a.get(k) != b.get(k):
                out.append(f'#{i} {k}: {a.get(k)} vs {b.get(k)}')
        if layout and not base and a['w'] and b['w'] and (abs(a['w'] - b['w']) > PX or abs(a['h'] - b['h']) > PX):
            out.append(f"#{i} size: {a['w']}x{a['h']} vs {b['w']}x{b['h']}")
    return out


def only_in(x, y, key):
    ny = collections.Counter(norm(m) for m in y.get(key, []))
    return sorted({norm(m) for m in x.get(key, []) if not ny[norm(m)]})


flags, stats = [], collections.Counter()
for url, b in R['B'].items():
    a, a2, c = R['A'].get(url), R['A2'].get(url), R['C'].get(url)
    if not c:
        continue
    stats['pages'] += 1
    for s, r in (('B', b), ('C', c)):
        if r.get('session_lost'):
            stats[f'session_lost_{s}'] += 1
    t = (b.get('trace') or {}).get('calls', {})
    stats['B pages with select API calls'] += bool(t)
    stats['B pages with a base-select select'] += any(x['app'] == 'base-select' for x in b.get('selects', []))
    if a:
        stats['A pages with a base-select select'] += any(x['app'] == 'base-select' for x in a.get('selects', []))
    f = {'url': url}
    d = sel_diff(c, b, expect_base=True)
    if d:
        f['feature'] = d
    e = only_in(b, c, 'errors')
    if e:
        f['feature_errors'] = e
    m = only_in(b, c, 'console')
    if m:
        f['feature_console'] = m
    if a and a2 and not sel_diff(a, a2, layout=False):
        if not sel_diff(a, c, layout=False):
            d = sel_diff(a, b, layout=False)
            if d:
                f['vs_ref'] = d
        base = []
        if a.get('count') == b.get('count'):
            for i, (x, y) in enumerate(zip(a['selects'], b['selects'])):
                if x['app'] == 'base-select' and x['w'] and (
                        y['app'] != 'base-select' or abs(x['w'] - y['w']) > max(20, 0.25 * x['w'])
                        or abs(x['h'] - y['h']) > max(10, 0.25 * x['h'])):
                    base.append(f"#{i} A {x['app']} {x['w']}x{x['h']} {x['display']} vs B {y['app']} "
                                f"{y['w']}x{y['h']} {y['display']}")
        if base:
            f['base'] = base
    if len(f) > 1:
        flags.append(f)
        for k in f:
            if k != 'url':
                stats[f'flag {k}'] += 1

json.dump({'stats': dict(stats), 'flags': flags}, sys.stdout, indent=1)
print()
