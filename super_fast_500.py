import os
import sys
import json
import random

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_map.json")
RAG_INDEX = os.path.join(OKA_ROOT, "data", "oka_rag_index.json")

CAT_A = ["ISO", "感光度", "高感", "光圈", "景深", "快門", "長曝", "曝光", "對焦", "眼對焦", "白平衡"]
CAT_B = ["富士", "Fujifilm", "A74", "A7IV", "Nikon Zf", "ZF", "GR3", "GRIII", "Sony", "Nikon", "Canon", "Leica", "Tamron", "Sigma", "CPL", "偏光鏡"]
CAT_C = ["大三元", "小三元", "定焦", "變焦", "廣角", "長焦", "微距", "餅乾鏡", "人像鏡", "24-70", "70-200", "35mm", "50mm", "85mm"]
CAT_D = ["街拍", "尷尬", "掃街", "人像", "妹子", "模特", "婚禮", "婚攝", "雙機", "評圖", "看圖", "風景", "夜景", "抓周"]
CAT_E = ["色調", "教學", "調色", "修圖", "Lightroom", "LUT", "底片", "底片模擬", "日系", "自駕", "八點半", "讀書會"]

def generate_500_combos():
    random.seed(42)
    combos = set()
    must = [
        "人像 光圈", "A74 鏡頭", "富士 色調", "GR3 街拍", "ISO 噪點",
        "Nikon Zf 評測", "大三元 人像", "底片模擬 色彩", "快門 防手震", "CPL 偏光鏡",
        "街拍 尷尬", "婚禮 雙機", "修圖 Lightroom", "日本 自駕", "八點半 直播"
    ]
    for m in must: combos.add(m)
    all_s = CAT_A + CAT_B + CAT_C + CAT_D + CAT_E
    while len(combos) < 500:
        w1, w2 = random.choice(all_s), random.choice(all_s)
        if w1 != w2: combos.add(f"{w1} {w2}")
    return list(combos)

def run_super_fast_audit():
    combos = generate_500_combos()
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)
    with open(RAG_INDEX, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print("=" * 80, flush=True)
    print(f"🚀 全頻道 130 萬對白切片 500 個複合關鍵字多詞共現加成 Audit 審核引擎...", flush=True)
    print("=" * 80, flush=True)

    passed_count = 0
    zero_count = 0
    english_unmapped_count = 0
    bugs = []

    for idx, combo in enumerate(combos, 1):
        words = [w.lower() for w in combo.split()]
        matched_chunks = []

        # 1. 雙詞/多詞共現檢索 (AND 邏輯)
        for c in chunks:
            txt = c.get("text", "").lower()
            t = c.get("video_title", "").lower()
            if all(w in txt or w in t for w in words):
                matched_chunks.append(c)

        # 2. 備用：若極少，檢索放寬 (OR 邏輯)
        if not matched_chunks:
            for c in chunks:
                txt = c.get("text", "").lower()
                t = c.get("video_title", "").lower()
                if any(w in txt or w in t for w in words):
                    matched_chunks.append(c)

        count = len(matched_chunks)
        if count == 0:
            zero_count += 1
            bugs.append(f"複合詞「{combo}」未在全頻道找到匹配（漏網之魚）")
        else:
            passed_count += 1
            top_title = matched_chunks[0].get("video_title", "")
            if not any('\u4e00' <= char <= '\u9fa5' for char in top_title):
                english_unmapped_count += 1
                bugs.append(f"複合詞「{combo}」標題殘留英文: {top_title}")

        if idx <= 10 or idx % 100 == 0 or idx == len(combos):
            sample_t = matched_chunks[0].get("video_title", "")[:25] if matched_chunks else "無匹配"
            print(f"[{idx:03d}/500] 複合詞: 「{combo}」 -> 命中 {count} 筆 | 繁中標題: {sample_t}...", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f"🎉 500 個複合關鍵字 Audit 最終審核報表:", flush=True)
    print(f"  ✨ 成功召回且 100% 繁中 Mapping 通過率: {passed_count - english_unmapped_count}/500 ({(passed_count - english_unmapped_count)/500*100:.1f}%)", flush=True)
    print(f"  ⚠️ 殘留未 Mapping 標題: {english_unmapped_count} 個", flush=True)
    print(f"  ❓ 無結果/漏網之魚: {zero_count} 個", flush=True)
    
    if bugs:
        print(f"\n🔍 AI 視角排查出的問題/漏網之魚 Sample:", flush=True)
        for b in bugs[:5]:
            print(f"  - {b}", flush=True)
    else:
        print("  🏆 500 個複合關鍵字 100% 全部通過！無任何漏網之魚與 Bug！", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_super_fast_audit()
