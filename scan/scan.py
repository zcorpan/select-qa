# Scan local Common Crawl WARCs for <select> usage patterns. Usage:
#   .venv/bin/python scan/scan.py ~/git/commoncrawl/cc-data/CC-MAIN-2026-39 scan/pages.jsonl
import glob, json, os, re, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cc import html_responses

SELECT = re.compile(r'<select\b', re.I)
BLOCK = re.compile(r'<select\b[^>]*>(.*?)</select\s*>', re.I | re.S)
TAG = re.compile(r'<([a-zA-Z][\w-]*)')
ALLOWED = {'option', 'optgroup', 'hr', 'script', 'template', 'noscript'}
BASE = re.compile(r'base-select|::picker\(select\)|<selectedcontent\b|::picker-icon|::checkmark', re.I)
LIBS = {
    'select2': re.compile(r'select2(\.min)?\.(js|css)|\.select2\(', re.I),
    'chosen': re.compile(r'chosen(\.jquery)?(\.min)?\.(js|css)|\.chosen\(', re.I),
    'selectize': re.compile(r'selectize(\.min)?\.(js|css)', re.I),
    'tom-select': re.compile(r'(?<![\w-])tom-select', re.I),
    'choices': re.compile(r'choices(\.min)?\.(js|css)', re.I),
    'bootstrap-select': re.compile(r'bootstrap-select', re.I),
    'nice-select': re.compile(r'nice-select|niceSelect\(', re.I),
    'slimselect': re.compile(r'slim-?select', re.I),
    'sumoselect': re.compile(r'sumoselect', re.I),
}


def scan(path):
    out, seen = [], 0
    for url, html in html_responses(path):
        seen += 1
        n = len(SELECT.findall(html))
        if not n:
            continue
        rich = {}
        for m in BLOCK.finditer(html):
            for t in TAG.findall(m.group(1)):
                t = t.lower()
                if t not in ALLOWED:
                    rich[t] = rich.get(t, 0) + 1
        out.append({
            'url': url, 'warc': os.path.basename(path), 'selects': n,
            'rich': rich, 'base_select': bool(BASE.search(html)),
            'libs': [k for k, r in LIBS.items() if r.search(html)],
            'base_hits': sorted({m.group(0).lower() for m in BASE.finditer(html)}),
            'complete': bool(re.search(r'</(body|html)>\s*$', html[-2000:], re.I)),
        })
    return path, seen, out


if __name__ == '__main__':
    warcs = sorted(glob.glob(os.path.join(os.path.expanduser(sys.argv[1]), '*.warc.gz')))
    counts = {}
    with Pool(min(12, os.cpu_count())) as pool, open(sys.argv[2], 'w') as f:
        for path, seen, rows in pool.imap_unordered(scan, warcs):
            counts[os.path.basename(path)] = seen
            for r in rows:
                f.write(json.dumps(r) + '\n')
            print(os.path.basename(path), seen, len(rows), flush=True)
    json.dump(counts, open(sys.argv[2].replace('.jsonl', '-html-counts.json'), 'w'), indent=1)
