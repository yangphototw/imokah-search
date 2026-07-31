import time
import sys

t0 = time.time()
print(f"[{time.time()-t0:.3f}s] 開始 import...", flush=True)

import ai_oka
print(f"[{time.time()-t0:.3f}s] import 完成", flush=True)

t1 = time.time()
vmap = ai_oka.get_video_map()
print(f"[{time.time()-t0:.3f}s] get_video_map 完成 ({time.time()-t1:.3f}s)", flush=True)

t2 = time.time()
sub_queries = ["彰化", "ISO"]
sub_query_terms_list = [ai_oka.expand_query_terms(sq) for sq in sub_queries]
print(f"[{time.time()-t0:.3f}s] expand_query_terms 完成 ({time.time()-t2:.3f}s)", flush=True)

t3 = time.time()
rag_hits = ai_oka.search_transcript_rag("彰化 ISO", top_k=100)
print(f"[{time.time()-t0:.3f}s] search_transcript_rag 完成 ({time.time()-t3:.3f}s)", flush=True)

t4 = time.time()
for r in rag_hits[:10]:
    v_id = ""
    raw_t = r.get('video_title', '')
    final_title = ai_oka.get_clean_title(v_id, raw_t)
print(f"[{time.time()-t0:.3f}s] get_clean_title 完成 ({time.time()-t4:.3f}s)", flush=True)
