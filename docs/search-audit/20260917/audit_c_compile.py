import json,pathlib
root=pathlib.Path(__file__).resolve().parent
out={'reviewer':'c','scope':{'query_numbers':[141,200],'method':'每批10詞，讀既有摘要與包內命中對應的完整原段落；含必要相鄰段落。full_source_read 指所列段落全文，不代表整部影片。只判斷包內候選，未對全部6383影片／查詢配對做語意通過聲明。'},'queries':[]}
for f in sorted(root.glob('decisions-c-*.json')):
    start=int(f.stem.split('-')[-1])
    qs=json.loads((root/f'review-{start:03d}-{start+9:03d}.json').read_text(encoding='utf-8-sig'))
    ds=json.loads(f.read_text(encoding='utf-8'))
    assert len(qs)==len(ds)==10
    for q,d in zip(qs,ds):
        assert q['number']==d['number']
        o={'number':q['number'],'query':q['query'],'returned':[],'missing':[],'conclusion':d['conclusion'],'note':d['note']}
        for typ,key in [('returned','returned_to_review'),('missing','missing_to_review')]:
            assert len(q[key])==len(d[typ]),(q['number'],typ)
            for e,a in zip(q[key],d[typ]):
                pids=[]
                for s in (e.get('hits') or [e.get('source')])+[e.get('intended_source')]:
                    if s and s['paragraph_id'] not in pids:pids.append(s['paragraph_id'])
                if len(a)>2:
                    pids=list(dict.fromkeys(pids+a[2]))
                v={'id':e['id'],'verdict':a[0],'reason':a[1],'paragraph_ids':pids,'full_source_read':bool(pids)}
                if typ=='returned': v.update(rank=e['rank'],full_match=e.get('full_match'))
                if e['id'] in d.get('ambiguous_'+typ,[]):v['intent_ambiguity']=True
                assert v['verdict'] not in ['irrelevant','should_include'] or v['full_source_read']
                o[typ].append(v)
        for typ in ['returned','missing']:
            for v in d.get('extra_'+typ,[]):
                assert v.get('extra_source') is True
                assert v['verdict'] not in ['irrelevant','should_include'] or v['full_source_read']
                o[typ].append(v)
        out['queries'].append(o)
(root/'semantic-c.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('Saved',len(out['queries']),'queries;',sum(len(q['returned']) for q in out['queries']),'returned;',sum(len(q['missing']) for q in out['queries']),'missing')
