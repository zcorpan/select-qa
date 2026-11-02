# Print local.py results side by side. Usage: python3 local_report.py local-out/run1.json
import json, sys
r = json.load(open(sys.argv[1]))
for t in [k for k in next(iter(r.values())) if k != 'version']:
    print('==', t)
    for s in r:
        print(' ', s, r[s]['version'])
        for step, st in r[s][t]:
            print('    %-17s app=%s disp=%s rect=%s val=%s idx=%s open=%s act=%s sc=%r log=%s' % (
                step, st['app'], st['display'], st['rect'], st['value'], st['idx'], st['open'], st.get('active'),
                (st['selectedcontent'] or '')[:50], st['log']))
