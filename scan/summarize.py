# Recompute the scan counts cited in the README. Usage: python3 scan/summarize.py
import collections, json, os
d = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(d, 'pages.jsonl'))]
total = sum(json.load(open(os.path.join(d, 'pages-html-counts.json'))).values())
rich = [r for r in rows if r['rich']]
print(f'HTML responses: {total}; with <select>: {len(rows)} ({len(rows)/total:.1%})')
print(f'with non-option content inside a select: {len(rich)}; base-select/::picker/selectedcontent: '
      f'{sum(r["base_select"] for r in rows)}')
tags = collections.Counter(t for r in rich for t in r['rich'])
print('pages per tag inside select:', tags.most_common(15))
print('libraries (pages):', collections.Counter(l for r in rows for l in r['libs']).most_common())
