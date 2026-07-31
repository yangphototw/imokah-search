import os
import sys
import json
import random

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_oka import hybrid_search_oka

# 基礎關鍵字種子庫 (相機、鏡頭、主題、參數、後製、旅行)
CAT_A = ["ISO", "感光度", "高感", "光圈", "景深", "快門", "長曝", "曝光", "對焦", "眼對焦", "白平衡"]
CAT_B = ["富士", "Fujifilm", "A74", "A7IV", "Nikon Zf", "ZF", "GR3", "GRIII", "Sony", "Nikon", "Canon", "Leica", "Tamron", "Sigma", "CPL", "偏光鏡"]
CAT_C = ["大三元", "小三元", "定焦", "變焦", "廣角", "長焦", "微距", "餅乾鏡", "人像鏡", "24-70", "70-200", "35mm", "50mm", "85mm"]
CAT_D = ["街拍", "尷尬", "掃街", "人像", "妹子", "模特", "婚禮", "婚攝", "雙機", "評圖", "看圖", "風景", "夜景", "抓周"]
CAT_E = ["色調", "教學", "調色", "修圖", "Lightroom", "LUT", "底片", "底片模擬", "日系", "自駕", "八點半", "讀書會"]

def generate_500_combinatorial_keywords():
    combo_set = set()
    random.seed(42) # 保持測試可重複性
    
    # 手動精選關鍵 100 區
    must_have = [
        "人像 光圈", "A74 鏡頭", "富士 色調", "GR3 街拍", "ISO 噪點",
        "Nikon Zf 評測", "大三元 人像", "底片模擬 色彩", "快門 防手震", "CPL 偏光鏡",
        "街拍 尷尬", "婚禮 雙機", "修圖 Lightroom", "日本 自駕", "八點半 直播"
    ]
    for m in must_have:
        combo_set.add(m)

    all_seed = CAT_A + CAT_B + CAT_C + CAT_D + CAT_E
    
    while len(combo_set) < 500:
        w1 = random.choice(all_seed)
        w2 = random.choice(all_seed)
        if w1 != w2:
            combo = f"{w1} {w2}"
            combo_set.add(combo)

    return list(combo_set)

def run_500_audit():
    keywords_500 = generate_500_combinatorial_keywords()
    print("=" * 80, flush=True)
    print(f"🧪 啟動 500 個複合關鍵字全自動 Audit 檢測 (如：人像 光圈, A74 鏡頭)...", flush=True)
    print("=" * 80, flush=True)

    passed_count = 0
    zero_count = 0
    title_unmapped_count = 0
    bugs_found = []

    for idx, kw in enumerate(keywords_500, 1):
        try:
            res = hybrid_search_oka(kw, top_k=20)
            c = len(res)

            # AI 視角自動評估：檢查標題與對白
            pure_eng = [r['video_title'] for r in res if not any('\u4e00' <= char <= '\u9fa5' for char in r['video_title'])]

            if c == 0:
                zero_count += 1
                bugs_found.append(f"複合詞「{kw}」無召回結果")
                if idx <= 20 or idx % 50 == 0:
                    print(f"[{idx:03d}/500] ❓ 複合詞: 「{kw}」 -> 0 筆命中", flush=True)
            else:
                passed_count += 1
                if pure_eng:
                    title_unmapped_count += 1
                    bugs_found.append(f"複合詞「{kw}」包含待 Mapping 標題: {pure_eng[0]}")
                    if idx <= 20 or idx % 50 == 0:
                        print(f"[{idx:03d}/500] ⚠️ 複合詞: 「{kw}」 -> 命中 {c} 筆 | 待 Mapping: {pure_eng[0][:20]}...", flush=True)
                else:
                    top_t = res[0]['video_title'][:25]
                    if idx <= 20 or idx % 50 == 0:
                        print(f"[{idx:03d}/500] ✅ 複合詞: 「{kw}」 -> 命中 {c} 筆 | 代表標題: {top_t}...", flush=True)

        except Exception as e:
            bugs_found.append(f"複合詞「{kw}」拋出例外: {e}")

    print("\n" + "=" * 80, flush=True)
    print(f"🎉 500 個複合關鍵字 Audit 最終審核報告:", flush=True)
    print(f"  ✨ 成功召回且 100% 繁中標題 Mapping: {passed_count - title_unmapped_count}/500 個 ({(passed_count - title_unmapped_count)/500*100:.1f}%)", flush=True)
    print(f"  ⚠️ 殘留未 Mapping 標題: {title_unmapped_count} 個", flush=True)
    print(f"  ❓ 無結果/漏網之魚數量: {zero_count} 個", flush=True)
    
    if bugs_found:
        print(f"\n🔍 AI 視角排查出的潛在 Bug/漏網之魚 Sample (前 5 個):", flush=True)
        for b in bugs_found[:5]:
            print(f"  - {b}", flush=True)
    else:
        print("  🏆 500 個複合關鍵字 100% 全部通過！無漏網之魚與 Bug！", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_500_audit()
