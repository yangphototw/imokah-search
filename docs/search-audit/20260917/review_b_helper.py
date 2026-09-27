import json,gzip,sys
from pathlib import Path
B=Path(__file__).parent
cache=B/'source-cache-b.json'
if cache.exists(): data=json.loads(cache.read_text(encoding='utf8'))
else:
 data={}
 for p in Path('public/paragraph-index').glob('*.json.gz'):
  data.update(json.load(gzip.open(p,'rt',encoding='utf8')))
 cache.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
def para(pid,neighbors=0):
 vid,idx=pid.rsplit(':',1); idx=int(idx)
 ps=data.get(vid,[])
 for p in ps[max(0,idx-neighbors):idx+neighbors+1]: print(p['id'],p['transcript'])
if sys.argv[1]=='batch':
 qs=json.loads((B/f'review-{sys.argv[2]}.json').read_text(encoding='utf8'))
 for q in qs:
  if len(sys.argv)>3 and q['number'] not in [int(n) for n in sys.argv[3:]]: continue
  print('\nQUERY',q['number'],q['query'],q['counts'])
  for key in ['returned_to_review','missing_to_review']:
   for x in q[key]:
    print('R' if key[0]=='r' else 'M',x.get('rank',''),x['id'],x['title']); print('摘要',x['summary'])
    hits=x.get('hits',[])
    if key[0]=='m':
     if x.get('source'): para(x['source']['paragraph_id'])
    elif hits:
     for h in hits: print('摘錄',h['paragraph_id'],h['excerpt'])
    else: print('無命中段落')
elif sys.argv[1]=='read':
 for pid in sys.argv[2:]: para(pid,1)
elif sys.argv[1]=='find':
 vid,term=sys.argv[2:4]
 for p in data.get(vid,[]):
  if term.lower() in p['transcript'].lower(): print(p['id'],p['transcript'])
