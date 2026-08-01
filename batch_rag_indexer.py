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
SEARCH_DB_FILE = os.path.join(OKA_ROOT, "data", "oka_search_db.json")

_RAG_INDEX_CACHE = None
_INVERTED_INDEX_CACHE = None
_SEARCH_DB_CACHE = None
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

def get_search_db():
    global _SEARCH_DB_CACHE
    if _SEARCH_DB_CACHE is None:
        _SEARCH_DB_CACHE = load_json_auto(SEARCH_DB_FILE)
    return _SEARCH_DB_CACHE or {}

def get_rag_chunks():
    global _RAG_INDEX_CACHE
    if _RAG_INDEX_CACHE is None:
        raw_list = load_json_auto(INDEX_FILE) or []
        _RAG_INDEX_CACHE = []
        while raw_list:
            c = raw_list.pop()
            if isinstance(c, dict):
                v_id = c.get('video_id') or c.get('source')
                ts = c.get('timestamp', '00:00')
                txt = c.get('text', '')
                st = c.get('start', 0)
                _RAG_INDEX_CACHE.append((v_id, ts, txt, st))
            else:
                _RAG_INDEX_CACHE.append(c)
        _RAG_INDEX_CACHE.reverse()
    return _RAG_INDEX_CACHE or []

def get_inverted_index():
    global _INVERTED_INDEX_CACHE
    if _INVERTED_INDEX_CACHE is None:
        _INVERTED_INDEX_CACHE = load_json_auto(INV_INDEX_FILE)
    return _INVERTED_INDEX_CACHE or {}

def search_transcript_rag(query, top_k=50):
    s_db = get_search_db()
    if s_db:
        keywords = [k.strip().lower() for k in query.split() if k.strip()]
        if not keywords:
            return []
        
        matched_chunks = []
        seen = set()
        for kw in keywords:
            items = s_db.get(kw, [])
            for item in items:
                v_id = item[0] if isinstance(item, (list, tuple)) else item.get('video_id')
                ts = item[1] if isinstance(item, (list, tuple)) else item.get('timestamp')
                key = f"{v_id}_{ts}"
                if key not in seen:
                    seen.add(key)
                    matched_chunks.append(item)
                    if len(matched_chunks) >= top_k:
                        break
            if len(matched_chunks) >= top_k:
                break
        
        results = []
        from ai_oka import get_video_map, get_clean_title
        vmap = get_video_map()
        
        for c in matched_chunks:
            if isinstance(c, (list, tuple)):
                v_id, timestamp, text, start = c[0], c[1], c[2], c[3]
            else:
                v_id = c.get('video_id') or c.get('source')
                timestamp = c.get('timestamp', '00:00')
                text = c.get('text', '')
                start = c.get('start', 0)
            
            raw_title = vmap.get(v_id, {}).get('title', '')
            clean_t = get_clean_title(v_id, raw_title)
            
            results.append({
                "video_title": clean_t,
                "timestamp": timestamp,
                "text": text,
                "start": start,
                "url": f"https://www.youtube.com/watch?v={v_id}&t={start}s"
            })
        return results

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

    from ai_oka import get_video_map, get_clean_title
    vmap = get_video_map()

    num_kw = len(keywords)
    matched = []
    for c in target_pool:
        if isinstance(c, tuple):
            vid, timestamp, txt_content, start = c
        else:
            vid = c.get('video_id') or c.get('source')
            timestamp = c.get('timestamp', '00:00')
            txt_content = c.get('text', '')
            start = c.get('start', 0)

        v_title = get_clean_title(vid, vmap.get(vid, {}).get('title', ''))
        
        score = 0
        txt_lower = txt_content.lower()
        title_lower = v_title.lower()

        for idx, kw in enumerate(keywords):
            pos_weight = 10 ** (num_kw - 1 - idx)
            if kw in txt_lower:
                cnt = min(txt_lower.count(kw), 5)
                score += cnt * pos_weight
            if kw in title_lower:
                cnt = min(title_lower.count(kw), 5)
                score += cnt * pos_weight * 5

        if score > 0:
            start_sec = int(start)
            item_dict = {
                "source": vid,
                "video_id": vid,
                "video_title": v_title,
                "start": start,
                "timestamp": timestamp,
                "text": txt_content,
                "url": f"https://www.youtube.com/watch?v={vid}&t={start_sec}s"
            }
            matched.append((score, item_dict))
            
    matched.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in matched[:top_k]]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = sys.argv[1]
        res = search_transcript_rag(q)
        print(f"極速倒排搜尋「{q}」結果 {len(res)} 筆:")
        for r in res[:5]:
            print(f"- [{r['video_title']} {r['timestamp']}]: {r['text']}")
