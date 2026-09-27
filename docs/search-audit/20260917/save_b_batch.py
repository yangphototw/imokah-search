import json,sys
from pathlib import Path
B=Path(__file__).parent
batch=sys.argv[1]
qs=json.loads((B/f'review-{batch}.json').read_text(encoding='utf8'))
ds=json.loads((B/f'decisions-b-{batch}.json').read_text(encoding='utf8'))
out=B/'semantic-b.json'
state=json.loads(out.read_text(encoding='utf8')) if out.exists() else {'reviewer':'b','scope':'71–140；只對指定 review 包的全部返回及未顯示候選做有限語意抽查。full_source_read 表示已讀所列原段落，並非整部影片。','queries':[]}
for q,d in zip(qs,ds,strict=True):
 assert q['number']==d['n']
 row={'number':q['number'],'query':q['query']}
 for k,src in [('returned','returned_to_review'),('missing','missing_to_review')]:
  row[k]=[]
  for x,v in zip(q[src],d[k],strict=True):
   e={'id':x['id'],'verdict':v[0],'reason':v[1],'full_source_read':v[2]}
   if k=='returned': e['rank']=x['rank']
   e['paragraph_ids']=v[3] if len(v)>3 else ([h['paragraph_id'] for h in x.get('hits',[])] if k=='returned' else [x['source']['paragraph_id']] if x.get('source') else [])
   packet_ids={h['paragraph_id'] for h in x.get('hits',[])}
   for sk in ['source','intended_source']:
    if x.get(sk): packet_ids.add(x[sk]['paragraph_id'])
   if any(pid not in packet_ids for pid in e['paragraph_ids']): e['extra_source']=True
   if len(v)>4: e.update(v[4])
   assert e['verdict'] not in ['should_include','irrelevant'] or e['full_source_read']
   row[k].append(e)
  for e in d.get('extra_'+k,[]):
   assert e['full_source_read'] and e['paragraph_ids']
   row[k].append({**e,'extra_source':True})
 row.update(conclusion=d['c'],note=d.get('note','僅涵蓋本包抽查項目。'))
 state['queries']=[r for r in state['queries'] if r['number']!=q['number']]+[row]
state['queries'].sort(key=lambda r:r['number'])
out.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
print('Saved',batch,'total',len(state['queries']))
