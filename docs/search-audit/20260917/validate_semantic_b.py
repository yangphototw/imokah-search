import json
from pathlib import Path
from collections import Counter
B=Path(__file__).parent
state=json.loads((B/'semantic-b.json').read_text(encoding='utf8'))
source=json.loads((B/'source-cache-b.json').read_text(encoding='utf8'))
source_ids={p['id'] for ps in source.values() for p in ps}
packets={q['number']:q for path in B.glob('review-*.json') for q in json.loads(path.read_text(encoding='utf8')) if 71<=q['number']<=140}
errors=[]
counts=Counter()
read_ids=set()
seen=set()
for q in state['queries']:
 n=q['number']; seen.add(n); p=packets[n]
 if q['query']!=p['query']: errors.append([n,'query_mismatch'])
 for key,packet_key in [('returned','returned_to_review'),('missing','missing_to_review')]:
  expected={x['id']:x for x in p[packet_key]}
  actual={x['id']:x for x in q[key]}
  if len(actual)!=len(q[key]): errors.append([n,key,'duplicate'])
  if set(expected)-set(actual): errors.append([n,key,'omitted',sorted(set(expected)-set(actual))])
  counts['packet_'+key]+=len(expected)
  for vid,x in actual.items():
   counts[key]+=1; counts[x['verdict']]+=1
   if vid not in expected:
    if not x.get('extra_source'): errors.append([n,key,vid,'extra_missing_flag'])
    counts['extra_items']+=1
   if x['verdict'] in ('should_include','irrelevant') and not x.get('full_source_read'): errors.append([n,key,vid,'required_full_read'])
   if x.get('full_source_read') and not x['paragraph_ids']: errors.append([n,key,vid,'no_full_source'])
   for pid in x['paragraph_ids']:
    if pid not in source_ids: errors.append([n,key,vid,'nonexistent_source',pid])
    if not pid.startswith(vid+':'): errors.append([n,key,vid,'other_video_source',pid])
    if x.get('full_source_read'): read_ids.add(pid)
   if x.get('intent_ambiguity'): counts['intent_ambiguity']+=1
   if key=='returned' and vid in expected and x['rank']!=expected[vid]['rank']: errors.append([n,key,vid,'rank_mismatch'])
if seen!=set(range(71,141)): errors.append(['wrong_range'])
if len(state['queries'])!=70: errors.append(['wrong_count'])
report={'scope':'71–140，全數包內項目＋標記的補查來源；非全庫所有結果','queries':len(state['queries']),'counts':dict(counts),'full_source_unique_paragraphs':len(read_ids),'errors':errors}
(B/'semantic-b-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
