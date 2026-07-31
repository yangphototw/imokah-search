import os
import sys
import json
import random

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_oka import hybrid_search_oka

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

def run_direct_audit():
    combos = generate_500_combos()
    print("=" * 80, flush=True)
    print(f"🧪 啟動 500 個複合關鍵字多詞共現加成全量 Audit 審核 (總計: {len(combos)} 個)...", flush=True)
    print("=" * 80, flush=True)

    passed_count = 0
    zero_count = 0
    title_unmapped_count = 0
    bugs_found = []

    # 取 前 30 個精選與抽樣作詳細輸出
    for idx, kw in enumerate(combos, 1):
        res = hybrid_search_oka(kw, top_k=10)
        c = len(res)
        pure_eng = [r['video_title'] for r in res if not any('\u4e00' <= char <= '\u9fa5' for char in r['video_title'])]

        if c == 0:
            zero_count += 1
            bugs_found.append(f"「{kw}」無召回筆數")
        else:
            passed_count += 1
            if pure_eng:
                title_unmapped_count += 1
                bugs_found.append(f"「{kw}」包含待 Mapping 標題: {pure_eng[0]}")

        if idx <= 15 or idx % 100 == 0 or idx == len(combos):
            top_t = res[0]['video_title'][:25] if res else "（無筆數）"
            print(f"[{idx:03d}/500] ✅ 複合關鍵字: 「{kw}」 -> 命中 {c} 筆 | 代表標題: {top_t}...", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f"🎉 500 個複合關鍵字 Audit 最終審核報表:", flush=True)
    print(f"  ✨ 成功召回且 100% 繁中 Mapping 通過率: {passed_count - title_unmapped_count}/500 ({(passed_count - title_unmapped_count)/500*100:.1f}%)", flush=True)
    print(f"  ⚠️ 殘留待 Mapping 標題: {title_unmapped_count} 個", flush=True)
    print(f"  ❓ 無結果/漏網之魚: {zero_count} 個", flush=True)
    if bugs_found:
        print(f"\n🔍 AI 視角排查出的潛在 Bug/漏網之魚 Sample:", flush=True)
        for b in bugs_found[:5]:
            print(f"  - {b}", flush=True)
    else:
        print("  🏆 500 個複合關鍵字 100% 全部通過！無任何漏網之魚與 Bug！", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_direct_audit()
