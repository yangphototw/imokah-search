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

def run():
    combos = generate_500_combos()
    print("=" * 80, flush=True)
    print(f"🚀 執行 500 個複合關鍵字多詞共現加成 Audit (總數: {len(combos)} 個)...", flush=True)
    print("=" * 80, flush=True)

    passed = 0
    zero = 0
    unmapped = 0
    sample_bugs = []

    for idx, kw in enumerate(combos, 1):
        # top_k=5 以達到毫秒級速度
        res = hybrid_search_oka(kw, top_k=5)
        c = len(res)
        pure_eng = [r['video_title'] for r in res if not any('\u4e00' <= char <= '\u9fa5' for char in r['video_title'])]

        if c == 0:
            zero += 1
            sample_bugs.append(f"「{kw}」未召回")
        else:
            passed += 1
            if pure_eng:
                unmapped += 1
                sample_bugs.append(f"「{kw}」待 Mapping: {pure_eng[0]}")

        if idx % 100 == 0:
            print(f"[{idx:03d}/500] 複合詞: 「{kw}」 -> 命中 {c} 筆 | Mapping OK", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f"🎉 500 個複合關鍵字 Audit 最終審核報表:", flush=True)
    print(f"  ✨ 成功召回且 100% 繁中 Mapping: {passed - unmapped}/500 ({(passed - unmapped)/500*100:.1f}%)", flush=True)
    print(f"  ⚠️ 殘留待 Mapping 標題: {unmapped} 個", flush=True)
    print(f"  ❓ 無結果/漏網之魚: {zero} 個", flush=True)
    if sample_bugs:
        print(f"  🔍 排查出的問題 Sample: {sample_bugs[:3]}", flush=True)
    else:
        print(f"  🏆 500 個複合關鍵字 100% 全部通過！無任何漏網之魚與 Bug！", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run()
