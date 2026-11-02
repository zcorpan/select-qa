# Print the customizable-select snippets (CSS around base-select/::picker, <select> blocks with
# <selectedcontent>) of the scan's base_select pages, one per host. Usage: extract_base.py DIR
import json, os, re, sys
from urllib.parse import urlsplit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cc import html_responses
rows = [json.loads(l) for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages.jsonl'))]
want = {}
for r in rows:
    if r['base_select']:
        want.setdefault(urlsplit(r['url']).hostname, (r['warc'], r['url']))
by_warc = {}
for h, (w, u) in want.items():
    by_warc.setdefault(w, set()).add(u)
for w, urls in by_warc.items():
    for url, html in html_responses(os.path.join(os.path.expanduser(sys.argv[1]), w)):
        if url not in urls:
            continue
        print('=====', urlsplit(url).hostname)
        seen = set()
        for m in re.finditer(r'base-select|::picker\(select\)', html):
            a = html.rfind('}', 0, m.start()) + 1
            b = html.find('}', m.end()) + 1
            snip = html[max(a, m.start() - 300):min(b, m.end() + 300)].strip()
            if snip not in seen:
                seen.add(snip); print('CSS:', snip[:500])
        for m in re.finditer(r'<select\b(?:(?!</select).)*?<selectedcontent.*?</select\s*>', html, re.S | re.I):
            print('HTML:', m.group(0)[:700]); break
