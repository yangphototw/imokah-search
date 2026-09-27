import sys,json,gzip,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
CACHE=ROOT/'source-cache-a.json'
if not CACHE.exists():
    data={}
    for p in pathlib.Path('public/paragraph-index').glob('*.json.gz'):
        data.update(json.load(gzip.open(p,'rt',encoding='utf-8')))
    CACHE.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
data=json.loads(CACHE.read_text(encoding='utf-8'))
mode=sys.argv[1]
if mode=='batch':
    n=int(sys.argv[2]); qs=json.loads((ROOT/f'review-{n:03}-{n+9:03}.json').read_text(encoding='utf-8'))
    for q in qs:
        if len(sys.argv)>3 and q['number'] not in [int(v) for v in sys.argv[3:]]: continue
        print(f'\nQ{q["number"]} {q["query"]} counts={q["counts"]}')
        for typ,key in [('R','returned_to_review'),('M','missing_to_review')]:
            for i,v in enumerate(q[key]):
                print(f'{typ}{i+1} {v["id"]} rank={v.get("rank", "-")} {v["title"]}\nS:{v["summary"]}')
                src=v.get('source') or v.get('intended_source') or next(iter(v.get('hits',[])),None)
                if typ=='R':
                    if src: print(f'E:{src["paragraph_id"]} '+src['excerpt'])
                    else: print('E: NONE')
                elif src:
                    pid=src['paragraph_id']; ix=int(pid.rsplit(':',1)[1]); ps=data[v['id']]
                    for p in ps:
                        if ix<=int(p['id'].rsplit(':',1)[1])<=ix+1: print(f'FULL:{p["id"]} {p["transcript"]}')
elif mode=='source':
    for spec in sys.argv[2:]:
        vid,nums=spec.rsplit(':',1)
        if '-' in nums: a,b=map(int,nums.split('-'))
        else: a=b=int(nums)
        for p in data[vid]:
            if a<=int(p['id'].rsplit(':',1)[1])<=b: print(f'FULL:{p["id"]} {p["transcript"]}')
elif mode=='find':
    vid=sys.argv[2]; terms=sys.argv[3:]
    for p in data[vid]:
        if any(t.lower() in p['transcript'].lower() for t in terms): print(f'FULL:{p["id"]} {p["transcript"]}')
elif mode=='save':
    n=int(sys.argv[2]); qs=json.loads((ROOT/f'review-{n:03}-{n+9:03}.json').read_text(encoding='utf-8'))
    ds=json.loads((ROOT/f'decisions-a-{n:03}.json').read_text(encoding='utf-8'))
    dest=ROOT/'semantic-a.json'
    out=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else {'reviewer':'a','scope':'第1–70詞包內全部有限語意樣本；非全部6383結果通過。full_source_read指列出原段落已閱讀，不代表整片逐字稿。','queries':[]}
    out['queries']=[q for q in out['queries'] if not n<=q['number']<=n+9]
    names={'u':'useful','m':'mention','i':'irrelevant','?':'unclear','s':'should_include'}
    for q,d in zip(qs,ds):
        assert q['number']==d['n']
        row={'number':q['number'],'query':q['query'],'returned':[],'missing':[],'conclusion':d['c'],'note':d.get('note','')}
        for key,dk,ok in [('returned_to_review','r','returned'),('missing_to_review','m','missing')]:
            assert len(q[key])==len(d.get(dk,[])),q['number']
            for v,x in zip(q[key],d.get(dk,[])):
                src=v.get('source') or v.get('intended_source') or next(iter(v.get('hits',[])),None)
                pids=x[2] if len(x)>2 else ([src['paragraph_id']] if src else [])
                full=x[3] if len(x)>3 else (dk=='m')
                result={'id':v['id'],'verdict':names[x[0]],'reason':x[1],'paragraph_ids':pids,'full_source_read':full}
                if dk=='r':result['rank']=v['rank']
                assert result['verdict'] not in ['should_include','irrelevant'] or full
                row[ok].append(result)
        row['missing'].extend(d.get('extra_missing',[]))
        out['queries'].append(row)
    out['queries'].sort(key=lambda q:q['number'])
    dest.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Saved {n}–{n+9}; total {len(out["queries"])} queries')
