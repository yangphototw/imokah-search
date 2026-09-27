import collections,json,pathlib
r=pathlib.Path(__file__).resolve().parent
d=json.loads((r/'semantic-c.json').read_text(encoding='utf-8'))
qs=d['queries']
assert [q['number'] for q in qs]==list(range(141,201))
sources=json.loads((r/'source-cache-c.json').read_text(encoding='utf-8'))
pidset={p['id'] for ps in sources.values() for p in ps}
packets={q['number']:q for start in range(141,201,10) for q in json.loads((r/f'review-{start:03d}-{start+9:03d}.json').read_text(encoding='utf-8-sig'))}
extra=[]
for q in qs:
    for typ,key in [('returned','returned_to_review'),('missing','missing_to_review')]:
        expected={v['id']:v for v in packets[q['number']][key]}
        actual={v['id']:v for v in q[typ]}
        assert len(actual)==len(q[typ]),(q['number'],'duplicate',typ)
        assert set(expected)<=set(actual),(q['number'],'missing packet entries')
        for vid,v in actual.items():
            assert v['verdict'] in ({'useful','mention','irrelevant','unclear'} if typ=='returned' else {'should_include','mention','irrelevant','unclear'})
            assert v['reason'] and v['paragraph_ids']
            assert all(pid in pidset for pid in v['paragraph_ids']),(q['number'],vid,'bad paragraph')
            assert all(pid.rsplit(':',1)[0]==vid for pid in v['paragraph_ids'])
            if v['verdict'] in ['should_include','irrelevant']:assert v['full_source_read'] is True
            if vid in expected and typ=='returned':
                assert v['rank']==expected[vid]['rank']
                assert v['full_match']==expected[vid]['full_match']
            if vid not in expected:
                assert v.get('extra_source') is True
                extra.append([q['number'],typ,vid])
amb=[(q['number'],v['id']) for q in qs for v in q['returned'] if v.get('intent_ambiguity')]
assert set(amb)=={(163,'2x8oQhQr1JY'),(163,'1rTmX4lV1mE'),(166,'EJ8iUj2iDBM'),(176,'raBkI6zpZTE')}
stats={'queries':len(qs),'returned':sum(len(q['returned']) for q in qs),'missing':sum(len(q['missing']) for q in qs),'packet_returned':sum(len(q['returned_to_review']) for q in packets.values()),'packet_missing':sum(len(q['missing_to_review']) for q in packets.values()),'distinct_evidence_paragraphs':len({pid for q in qs for t in ['returned','missing'] for v in q[t] for pid in v['paragraph_ids']}),'extra_sources':extra,'intent_ambiguity_entries':amb,'verdict_counts':{t:dict(collections.Counter(v['verdict'] for q in qs for v in q[t])) for t in ['returned','missing']},'validation':'All 60 queries, packet coverage, paragraph identities, flags, and original ranks/full_match verified.'}
(r/'validation-c.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(stats,ensure_ascii=False))
