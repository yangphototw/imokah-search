import os
import sys
import json
import re
from functools import lru_cache
from batch_rag_indexer import search_transcript_rag

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_map.json")
TITLE_ZH_MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_title_zh_mapping.json")
LLM_SUMMARIES_FILE = os.path.join(OKA_ROOT, "data", "oka_llm_summaries.json")
AI_SUMMARIES_FILE = os.path.join(OKA_ROOT, "data", "oka_ai_summaries.json")
CLEANED_TRANSCRIPTS_FILE = os.path.join(OKA_ROOT, "data", "oka_cleaned_transcripts.json")

_VMAP_CACHE = None
_TITLE_ZH_CACHE = None
_LLM_SUMMARIES_CACHE = None
_CLEANED_TRANSCRIPTS_CACHE = None

# 全量解耦與專業 Audit 攝影專有名詞同義詞圖譜
ALL_CAMERA_SYNONYMS = {
    # 曝光三要素
    "iso": ["iso", "感光度", "感光", "高感", "噪點", "雙原生", "原生iso", "基准iso", "純淨度"],
    "感光度": ["感光度", "iso", "感光", "高感", "噪點", "雙原生", "原生iso"],
    "高感": ["高感", "iso", "感光度", "噪點", "夜拍", "夜景"],
    "噪點": ["噪點", "iso", "高感", "純淨度", "降噪"],
    "光圈": ["光圈", "aperture", "f值", "f1.4", "f1.8", "f2.8", "大光圈", "小光圈", "景深", "散景", "虛化"],
    "景深": ["景深", "光圈", "虛化", "散景", "背景虛化"],
    "虛化": ["虛化", "景深", "散景", "光圈"],
    "快門": ["快門", "shutter", "快門速度", "快門轉盤", "電子快門", "機械快門", "快門聲", "安全快門"],
    
    # 🚀 解耦 1: 慢快門與長曝（絕不混入普通快門）
    "慢快門": ["慢快門", "慢速快門", "長曝", "長時間曝光", "車軌", "流水", "絲絹感", "搖鏡", "panning", "b快門", "腳架"],
    "慢速快門": ["慢速快門", "慢快門", "長曝", "長時間曝光", "車軌", "流水", "絲絹感", "b快門"],
    "長曝": ["長曝", "長時間曝光", "慢快門", "慢速快門", "腳架", "車軌", "流水", "b快門"],

    # 🚀 解耦 2: 傳統底片膠卷 vs 富士底片模擬 (Film Simulation)
    "底片": ["底片", "底片相機", "膠卷", "底片膠卷", "135底片", "120底片", "沖洗", "銀鹽"],
    "底片模擬": ["底片模擬", "富士底片模擬", "film simulation", "classic neg", "nc", "cc", "發色檔", "底片配方"],
    
    # 🚀 解耦 3: 大三元 vs 小三元
    "大三元": ["大三元", "f2.8變焦", "16-35 f2.8", "24-70 f2.8", "70-200 f2.8"],
    "小三元": ["小三元", "f4變焦", "16-35 f4", "24-105 f4", "70-200 f4"],
    
    # 🚀 解耦 4: 人像攝影 vs 人像專用鏡頭
    "人像": ["人像", "寫真", "model", "模特", "妹子", "人像拍攝"],
    "人像鏡頭": ["人像鏡頭", "人像焦段", "85mm", "135mm", "50mm f1.2", "85mm f1.4", "85mm f1.8", "虛化人像"],

    # 光學與相機專有名詞
    "曝光": ["曝光", "exposure", "曝光補償", "測光", "過曝", "欠曝", "直方圖", "動態範圍", "大光比"],
    "動態範圍": ["動態範圍", "曝光", "寬容度", "高光溢出", "暗部拉亮"],
    "對焦": ["對焦", "focus", "眼對焦", "追焦", "手動對焦", "單點對焦", "af", "mf", "對焦點"],
    "白平衡": ["白平衡", "wb", "色溫", "k值", "偏色", "發色", "色彩科學"],
    "定焦": ["定焦", "35mm", "50mm", "85mm", "大光圈定焦"],
    "變焦": ["變焦", "24-70", "70-200", "24-105"],
    "廣角": ["廣角", "超廣角", "14-24", "16-35", "20mm", "24mm"],
    
    # 相機品牌與熱門機型
    "富士": ["富士", "fuji", "fujifilm", "x100v", "x100vi", "x100", "x-t5", "x-t50", "x-e4", "x-m5", "x-pro3", "gfx"],
    "索尼": ["索尼", "sony", "a74", "a7iv", "a7m4", "a7r5", "a7c", "a7c2", "fx3", "zv-e10"],
    "尼康": ["尼康", "nikon", "zf", "z8", "z9", "z6", "z6ii", "zfc"],
    "理光": ["理光", "ricoh", "gr3", "griii", "gr3x", "gr2", "gr"],
    "gr3": ["gr3", "griii", "gr3x", "理光gr3", "快照模式", "snap模式"],
    "佳能": ["佳能", "canon", "r5", "r6", "r6ii", "r8", "eos r"],
    "萊卡": ["萊卡", "徠卡", "leica", "m10", "m11", "q2", "q3"],
    "蔡司": ["蔡司", "zeiss", "蔡絲", "菜絲", "carl zeiss"],
    "蔡絲": ["蔡絲", "蔡司", "zeiss", "菜絲"],
    "cpl": ["cpl", "偏光鏡", "偏振鏡"],
    "偏光鏡": ["偏光鏡", "cpl", "偏振鏡"],
    "nd": ["nd", "減光鏡"],
    "減光鏡": ["減光鏡", "nd"],
    "街拍": ["街拍", "快照", "snap", "street photography", "掃街", "抓拍", "腰平取景"],
    "調色": ["調色", "修圖", "lightroom", "lut", "色調", "後製", "hsl"],
    "鏡頭": ["鏡頭", "焦段", "副廠", "騰龍", "適馬", "卡口"]
}

def clean_homophone_typos(text):
    if not text: return text
    t = text
    brand_map = {
        "蔡絲": "蔡司",
        "菜絲": "蔡司",
        "卡爾蔡絲": "卡爾蔡司",
        "蔡絲鏡頭": "蔡司鏡頭",
        "菜絲鏡頭": "蔡司鏡頭"
    }
    for old_k, new_v in brand_map.items():
        t = t.replace(old_k, new_v)

    name_map = {
        "我是刀子": "我是道慈",
        "我是道子": "我是道慈",
        "我是到此": "我是道慈",
        "我是道士": "我是道慈",
        "道士老師": "道慈老師",
        "刀子老師": "道慈老師",
        "道子老師": "道慈老師",
        "到此老師": "道慈老師",
        "到慈老師": "道慈老師",
        "導詞老師": "道慈老師",
        "倒此老師": "道慈老師",
        "刀子": "道慈",
        "道子": "道慈",
        "到慈": "道慈",
        "導詞": "道慈",
        "倒此": "道慈"
    }
    for old_k, new_v in name_map.items():
        t = t.replace(old_k, new_v)

    t = re.sub(r'(穿很暖的|我是)道士', r'\1道慈', t)
    t = re.sub(r'到此(?=說|認為|表示|分享|講|覺得|實測|帶|去|在|的)', '道慈', t)
    return t

import gzip

def load_json_auto(path):
    gz_path = path + ".gz"
    if os.path.exists(gz_path):
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            return json.load(f)
    elif os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_cleaned_transcripts():
    global _CLEANED_TRANSCRIPTS_CACHE
    if _CLEANED_TRANSCRIPTS_CACHE is None:
        _CLEANED_TRANSCRIPTS_CACHE = load_json_auto(CLEANED_TRANSCRIPTS_FILE)
    return _CLEANED_TRANSCRIPTS_CACHE or {}

def get_title_zh_map():
    global _TITLE_ZH_CACHE
    if _TITLE_ZH_CACHE is None:
        _TITLE_ZH_CACHE = load_json_auto(TITLE_ZH_MAP_FILE)
    return _TITLE_ZH_CACHE or {}

def get_video_map():
    global _VMAP_CACHE
    if _VMAP_CACHE is None:
        _VMAP_CACHE = load_json_auto(MAP_FILE)
    return _VMAP_CACHE or {}

def get_llm_summaries():
    global _LLM_SUMMARIES_CACHE
    if _LLM_SUMMARIES_CACHE is None:
        _LLM_SUMMARIES_CACHE = {}
        raw_llm = load_json_auto(LLM_SUMMARIES_FILE)
        if raw_llm:
            for k, v in raw_llm.items():
                _LLM_SUMMARIES_CACHE[k] = clean_homophone_typos(v)
        
        fallback_sums = load_json_auto(AI_SUMMARIES_FILE)
        if fallback_sums:
            for k, v in fallback_sums.items():
                if k not in _LLM_SUMMARIES_CACHE:
                    _LLM_SUMMARIES_CACHE[k] = clean_homophone_typos(v)
    return _LLM_SUMMARIES_CACHE or {}

def get_clean_title(v_id, fallback_title):
    zh_map = get_title_zh_map()
    if v_id and v_id in zh_map:
        return clean_homophone_typos(zh_map[v_id])
    
    raw_t = fallback_title or "【我都OK啊】攝影專題對話精華"
    return clean_homophone_typos(raw_t)

def expand_query_terms(query):
    q_lower = query.strip().lower()
    terms = set([q_lower])

    for key, syns in ALL_CAMERA_SYNONYMS.items():
        if key == q_lower:
            for s in syns:
                terms.add(s)

    words = re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fa5]+', q_lower)
    for w in words:
        w_lower = w.lower()
        if w_lower in ALL_CAMERA_SYNONYMS:
            for s in ALL_CAMERA_SYNONYMS[w_lower]:
                terms.add(s)

    return list(terms)

def extract_topic_tag(text):
    t_lower = text.lower()
    if any(k in t_lower for k in ["慢快門", "慢速快門", "長曝", "長時間曝光", "車軌", "流水"]):
        return "⏱️ 【慢快門與長曝技巧】"
    if any(k in t_lower for k in ["iso", "感光度", "高感", "噪點"]):
        return "🎨 【ISO 與感光度表現】"
    if any(k in t_lower for k in ["光圈", "aperture", "f值", "景深", "虛化", "散景"]):
        return "📷 【光圈與景深控制】"
    if any(k in t_lower for k in ["快門", "shutter", "快門速度"]):
        return "⏱️ 【快門速度與動態】"
    if any(k in t_lower for k in ["對焦", "追焦", "眼對焦", "對焦速度"]):
        return "🎯 【對焦性能與反應】"
    if any(k in t_lower for k in ["底片模擬", "film simulation", "classic neg"]):
        return "🎨 【富士底片模擬與配方】"
    if any(k in t_lower for k in ["鏡頭", "焦段", "35mm", "50mm", "85mm", "24-70", "副廠", "騰龍", "適馬", "蔡司", "蔡絲"]):
        return "📷 【鏡頭搭配與焦段選擇】"
    if any(k in t_lower for k in ["畫質", "發色", "色彩", "動態範圍", "調色"]):
        return "🎨 【畫質色彩與調色表現】"
    return "💡 【核心觀點與建議】"

def format_smart_match_reason(query, found_words, is_tier_a=False, is_tier_c=False):
    unique_words = list(set(found_words))
    q_clean = query.strip()

    if is_tier_a or is_tier_c:
        return f"🏆 「{q_clean}」主題精華影片"
    
    if unique_words:
        matched_str = ", ".join(unique_words[:3])
        return f"含關鍵字: {matched_str}"
    
    return f"含關鍵字: {q_clean}"

def _hybrid_search_impl(query, top_k=500):
    vmap = get_video_map()
    llm_sums = get_llm_summaries()
    cleaned_transcripts = get_cleaned_transcripts()

    sub_queries = [sq.strip() for sq in query.split() if sq.strip()]
    if not sub_queries:
        sub_queries = [query]

    total_sub_count = len(sub_queries)
    sub_query_terms_list = [expand_query_terms(sq) for sq in sub_queries]
    
    seen_urls = set()
    scored_items = []

    # Layer 1: 全量標題比對
    for v_id, meta in vmap.items():
        title = get_clean_title(v_id, meta.get("title", ""))
        title_lower = title.lower()

        sub_hits = 0
        weighted_score = 0
        real_found_words = []

        for idx, t_list in enumerate(sub_query_terms_list):
            pos_weight = 10 ** (total_sub_count - 1 - idx)
            term_hit = False
            for term in t_list:
                if term in title_lower:
                    term_hit = True
                    real_found_words.append(term)
                    cnt = min(title_lower.count(term), 5)
                    weighted_score += cnt * pos_weight * 1000
            if term_hit:
                sub_hits += 1
                weighted_score += pos_weight * 10000

        if sub_hits > 0:
            url = f"https://www.youtube.com/watch?v={v_id}&t=0s"
            if url not in seen_urls:
                seen_urls.add(url)

                title_all_matched = (sub_hits == total_sub_count)
                
                if title_all_matched:
                    score = 2000000 + weighted_score
                    match_reason = format_smart_match_reason(query, real_found_words, is_tier_a=True)
                else:
                    score = weighted_score
                    match_reason = format_smart_match_reason(query, real_found_words)

                summary = clean_homophone_typos(llm_sums.get(url, f"影片標題包含「{query}」熱門主題討論"))

                scored_items.append((score, {
                    "video_title": title,
                    "timestamp": "00:00",
                    "text": title,
                    "summary": summary,
                    "topic_tag": "📌 【標題專題討論】",
                    "match_reason": match_reason,
                    "url": url,
                    "type": "標題精確匹配"
                }))

    # Layer 2: 對白深度檢索
    rag_hits = search_transcript_rag(" ".join(sub_queries), top_k=top_k)
    for r in rag_hits:
        url = r.get('url', '')
        if url not in seen_urls:
            seen_urls.add(url)

            raw_txt = r.get('text', '')
            txt = cleaned_transcripts.get(url, clean_homophone_typos(raw_txt))
            txt_lower = txt.lower()

            sub_hits = 0
            weighted_score = 0
            real_found_words = []

            for idx, t_list in enumerate(sub_query_terms_list):
                pos_weight = 10 ** (total_sub_count - 1 - idx)
                term_hit = False
                for t in t_list:
                    if t in txt_lower:
                        term_hit = True
                        cnt = min(txt_lower.count(t), 5)
                        weighted_score += cnt * pos_weight * 50
                        real_found_words.append(t)
                if term_hit:
                    sub_hits += 1
                    weighted_score += pos_weight * 5000

            if sub_hits > 0:
                transcript_all_matched = (sub_hits == total_sub_count)
                
                v_id = ""
                m = re.search(r'v=([a-zA-Z0-9_-]{11})', url)
                if m: v_id = m.group(1)
                raw_t = r.get('video_title', '')
                final_title = get_clean_title(v_id, raw_t)
                title_lower = final_title.lower()

                title_sub_hits = sum(1 for t_list in sub_query_terms_list if any(t in title_lower for t in t_list))
                title_all_matched = (title_sub_hits == total_sub_count)

                if title_all_matched and transcript_all_matched:
                    score = 2000000 + weighted_score
                    match_reason = format_smart_match_reason(query, real_found_words, is_tier_a=True)
                elif transcript_all_matched:
                    score = 1000000 + weighted_score
                    match_reason = format_smart_match_reason(query, real_found_words, is_tier_c=True)
                else:
                    score = weighted_score
                    match_reason = format_smart_match_reason(query, real_found_words)

                tag = extract_topic_tag(txt)
                summary = clean_homophone_typos(llm_sums.get(url, ""))
                if not summary:
                    summary = f"💡 攝影點評：探討「{query}」相關實務拍攝經驗與參數設定"

                scored_items.append((score, {
                    "video_title": final_title,
                    "timestamp": r.get('timestamp', ''),
                    "text": txt,
                    "summary": summary,
                    "topic_tag": tag,
                    "match_reason": match_reason,
                    "url": url,
                    "type": "對白同義詞檢索"
                }))

    scored_items.sort(key=lambda x: x[0], reverse=True)
    return tuple(scored_items[:top_k])

_SEARCH_CACHE = {}

def hybrid_search_oka(query, top_k=500):
    cache_key = f"{query.strip().lower()}_{top_k}"
    if cache_key in _SEARCH_CACHE:
        return _SEARCH_CACHE[cache_key]

    results = [item[1] for item in _hybrid_search_impl(query, top_k=top_k)]
    if len(_SEARCH_CACHE) > 500:
        _SEARCH_CACHE.clear()
    _SEARCH_CACHE[cache_key] = results
    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = sys.argv[1]
        res = hybrid_search_oka(q)
        print(f"🔍 同義詞解耦 Audit 測試「{q}」 (前 5 筆結果):", flush=True)
        for idx, r in enumerate(res[:5]):
            print(f"[{idx+1}] [{r['topic_tag']}] [{r['video_title']} {r['timestamp']}]\n    🎯 標籤: {r['match_reason']}\n    💡 摘要: {r['summary']}\n", flush=True)
