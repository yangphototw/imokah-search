import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_oka import hybrid_search_oka

# 定義 100 個涵蓋相機、鏡頭、主題、教學、大師與旅行的精選關鍵字
KEYWORDS = [
    # 器材 (30)
    "ISO", "感光度", "高感", "光圈", "景深", "虛化", "快門", "長曝", "曝光", "測光",
    "對焦", "眼對焦", "白平衡", "色溫", "富士", "Fujifilm", "X100V", "X100VI", "索尼", "Sony",
    "A74", "A7IV", "尼康", "Nikon", "Zf", "ZF", "理光", "Ricoh", "GR3", "GRIII",

    # 鏡頭 (20)
    "大三元", "小三元", "定焦", "變焦", "廣角", "超廣角", "長焦", "微距", "百微", "餅乾鏡",
    "人像鏡", "24-70", "70-200", "16-35", "35mm", "50mm", "85mm", "佳能", "Canon", "萊卡",

    # 主題與心法 (30)
    "街拍", "尷尬", "掃街", "人像", "妹子", "模特", "婚禮", "婚攝", "雙機", "評圖",
    "看圖", "點評", "風景", "夜景", "抓周", "二手機", "劃算", "線上課", "作法", "視角",
    "CPL", "偏光鏡", "ND", "減光鏡", "腳架", "相機包", "騰龍", "Tamron", "適馬", "Sigma",

    # 後製與頻道節目 (20)
    "色調", "教學", "調色", "修圖", "Lightroom", "LUT", "底片", "底片模擬", "膠片", "色彩配方",
    "日系", "顆粒", "八點半", "週三八點半", "攝影週報", "攝影研究所", "攝影讀書會", "森山大道", "布列松", "自駕"
]

def check_all():
    print("=" * 80, flush=True)
    print(f"🧪 啟動全頻道 100 個關鍵字 100% 標題 Mapping 與召回率 Audit 檢測...", flush=True)
    print("=" * 80, flush=True)

    passed_all = True
    mapped_count = 0
    unmapped_titles = []

    for idx, kw in enumerate(KEYWORDS, 1):
        res = hybrid_search_oka(kw, top_k=20)
        c = len(res)
        pure_eng = [r['video_title'] for r in res if not any('\u4e00' <= char <= '\u9fa5' for char in r['video_title'])]

        if pure_eng:
            unmapped_titles.extend(pure_eng)
            print(f"[{idx:03d}/100] ⚠️ 關鍵字: 「{kw}」 -> 發現殘留純英文標題: {pure_eng[0]}", flush=True)
            passed_all = False
        else:
            mapped_count += 1
            top = res[0]['video_title'][:25] if res else "（無筆數）"
            print(f"[{idx:03d}/100] ✅ 關鍵字: 「{kw}」 -> 命中 {c} 筆 | 標題: {top}...", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f"🎉 Audit 檢測結果報表:", flush=True)
    print(f"  ✨ 100% 繁體中文標題 Mapping 通過率: {mapped_count}/{len(KEYWORDS)} ({mapped_count/len(KEYWORDS)*100:.1f}%)", flush=True)
    if unmapped_titles:
        print(f"  ❌ 未 Mapping 標題數量: {len(set(unmapped_titles))} 個: {list(set(unmapped_titles))[:3]}", flush=True)
    else:
        print("  🏆 100 個關鍵字全部通過 100% 繁體中文 Mapping 檢驗，無任何英文自動翻譯殘留！", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    check_all()
