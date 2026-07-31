import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_oka import hybrid_search_oka

KEYWORDS_100 = [
    # 器材品牌與型號 (40 個)
    "ISO", "感光度", "高感", "噪點", "原生ISO", "光圈", "景深", "虛化", "快門", "長曝",
    "慢快門", "曝光", "測光", "曝光補償", "動態範圍", "白平衡", "色溫", "對焦", "追焦", "眼對焦",
    "富士", "Fujifilm", "Fuji", "X100V", "X100VI", "X-T5", "X-T50", "X-E4", "X-M5", "索尼",
    "Sony", "A74", "A7IV", "A7M4", "A7R5", "A7C2", "FX3", "ZV-E10", "尼康", "Nikon",
    "Zf", "ZF", "Z8", "Z9", "Z6", "Z6II", "Zfc", "理光", "Ricoh", "GR3",
    "GRIII", "GR3x", "佳能", "Canon", "R5", "R6II", "R8", "萊卡", "Leica", "騰龍",
    "Tamron", "適馬", "Sigma", "沃坦", "Wotancraft", "CPL", "偏光鏡", "ND", "減光鏡", "腳架",

    # 鏡頭與焦段 (20 個)
    "大三元", "小三元", "定焦", "變焦", "廣角", "超廣角", "長焦", "望遠", "微距", "百微",
    "餅乾鏡", "人像鏡", "24-70", "70-200", "16-35", "35mm", "50mm", "85mm", "14-24", "135mm",

    # 攝影主題與心法 (20 個)
    "街拍", "尷尬", "掃街", "人像", "妹子", "模特", "婚禮", "婚攝", "雙機", "評圖",
    "看圖", "點評", "風景", "夜景", "抓周", "二手機", "劃算", "線上課", "作法", "視角",

    # 後製調色與頻道節目 (20 個)
    "色調", "教學", "調色", "修圖", "Lightroom", "LUT", "底片", "底片模擬", "膠片", "色彩配方",
    "日系", "顆粒", "八點半", "週三八點半", "攝影週報", "攝影研究所", "攝影讀書會", "森山大道", "布列松", "自駕"
]

def run():
    print("=" * 80, flush=True)
    print(f"🚀 開始極速 100 個關鍵字全自動 Audit 檢測 (總計: {len(KEYWORDS_100)} 個)...", flush=True)
    print("=" * 80, flush=True)

    passed = 0
    zero = 0
    title_unmapped = 0

    for idx, kw in enumerate(KEYWORDS_100, 1):
        res = hybrid_search_oka(kw, top_k=20)
        c = len(res)
        pure_eng = [r['video_title'] for r in res if not any('\u4e00' <= char <= '\u9fa5' for char in r['video_title'])]

        if c == 0:
            zero += 1
            print(f"[{idx:03d}/100] ❓ 「{kw}」 -> 0 筆", flush=True)
        else:
            passed += 1
            if pure_eng:
                title_unmapped += 1
                print(f"[{idx:03d}/100] ⚠️ 「{kw}」 -> {c} 筆 | 待 Mapping 標題: {pure_eng[0][:20]}...", flush=True)
            else:
                top_t = res[0]['video_title'][:25]
                print(f"[{idx:03d}/100] ✅ 「{kw}」 -> {c} 筆 | 繁中標題: {top_t}...", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f"🎉 Audit 最終審核報表:", flush=True)
    print(f"  ✅ 正確召回與繁中 Mapping 成功: {passed - title_unmapped}/100 個關鍵字", flush=True)
    print(f"  ⚠️ 殘留待 Mapping: {title_unmapped} 個", flush=True)
    print(f"  ❓ 無結果: {zero} 個", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run()
