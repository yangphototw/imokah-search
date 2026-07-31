import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(OKA_ROOT, "data", "oka_rag_index.json")
INV_INDEX_FILE = os.path.join(OKA_ROOT, "data", "oka_inverted_index.json")

_RAG_INDEX_CACHE = None
import gzip

def load_json_auto(path):
    gz_path = path + ".gz"
    if os.path.exists(gz_path):
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            return json.load(f)
    elif os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def get_rag_chunks():
    global _RAG_INDEX_CACHE
    if _RAG_INDEX_CACHE is None:
        _RAG_INDEX_CACHE = load_json_auto(INDEX_FILE)
    return _RAG_INDEX_CACHE or []

def get_inverted_index():
    global _INVERTED_INDEX_CACHE
    if _INVERTED_INDEX_CACHE is None:
        _INVERTED_INDEX_CACHE = load_json_auto(INV_INDEX_FILE)
    return _INVERTED_INDEX_CACHE or {}

def search_transcript_rag(query, top_k=50):
    chunks = get_rag_chunks()
    if not chunks:
        return []
        
    keywords = [k.strip().lower() for k in query.split() if k.strip()]
    if not keywords:
        return []

    inv_map = get_inverted_index()
    
    # 秒級集合交集 (Sub-10ms Set Intersection)
    kw_sets = [set(inv_map[kw]) for kw in keywords if kw in inv_map]
    
    if kw_sets:
        intersect_indices = set.intersection(*kw_sets) if len(kw_sets) > 1 else kw_sets[0]
        if not intersect_indices:
            intersect_indices = set.union(*kw_sets)
        target_pool = [chunks[i] for i in list(intersect_indices)[:300]]
    else:
        target_pool = chunks[:500]

    num_kw = len(keywords)
    matched = []
    for c in target_pool:
        score = 0
        txt = c.get('text', '').lower()
        title = c.get('video_title', '').lower()
        
        for idx, kw in enumerate(keywords):
            pos_weight = 10 ** (num_kw - 1 - idx)
            if kw in txt:
                cnt = min(txt.count(kw), 5)
                score += cnt * pos_weight
            if kw in title:
                cnt = min(title.count(kw), 5)
                score += cnt * pos_weight * 5

        if score > 0:
            matched.append((score, c))
            
    matched.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in matched[:top_k]]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = sys.argv[1]
        res = search_transcript_rag(q)
        print(f"極速倒排搜尋「{q}」結果 {len(res)} 筆:")
        for r in res[:5]:
            print(f"- [{r['video_title']} {r['timestamp']}]: {r['text']}")
