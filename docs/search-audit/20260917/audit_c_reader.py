import gzip, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent
PUBLIC=ROOT.parents[2]/'public'/'paragraph-index'
cache=ROOT/'source-cache-c.json'
if not cache.exists():
    library={}
    for f in PUBLIC.glob('*.json.gz'):
        library.update(json.load(gzip.open(f,'rt',encoding='utf-8')))
    cache.write_text(json.dumps(library,ensure_ascii=False),encoding='utf-8')
library=json.loads(cache.read_text(encoding='utf-8'))
if sys.argv[1]=='find':
    vid=sys.argv[2]
    terms=sys.argv[3:]
    selected=set()
    ps=library[vid]
    for i,p in enumerate(ps):
        if any(t.lower() in p['transcript'].lower() for t in terms):
            selected.update(range(max(0,i-1),min(len(ps),i+2)))
    for i in sorted(selected):print(ps[i]['id'],ps[i]['transcript'])
    sys.exit()
if sys.argv[1]=='paragraphs':
    for pid in sys.argv[2:]:
        vid,idx=pid.rsplit(':',1)
        idx=int(idx)
        for p in library[vid]:
            if abs(int(p['id'].rsplit(':',1)[1])-idx)<=1:
                print(p['id'],p['transcript'])
    sys.exit()
start=int(sys.argv[1])
qs=json.loads((ROOT/f'review-{start:03d}-{start+9:03d}.json').read_text(encoding='utf-8-sig'))
if len(sys.argv)>2: qs=[q for q in qs if q['number'] in [int(v) for v in sys.argv[2:]]]
for q in qs:
    print('\nQUERY',q['number'],q['query'],'counts',q['counts'])
    for typ,key in [('RETURN','returned_to_review'),('MISSING','missing_to_review')]:
        for e in q[key]:
            print(typ,e.get('rank',''),e['id'],e['title'])
            print('SUMMARY',e['summary'])
            sources=e.get('hits') or [e.get('source')]
            pids=[]
            for s in sources:
                if s and s['paragraph_id'] not in pids: pids.append(s['paragraph_id'])
            other=e.get('intended_source')
            if other and other['paragraph_id'] not in pids: pids.append(other['paragraph_id'])
            for pid in pids:
                p=next((p for p in library[e['id']] if p['id']==pid),None)
                print('SOURCE',pid,p['transcript'] if p else 'NOT FOUND')
            if not pids: print('NO SOURCE')
