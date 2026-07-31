import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_oka import hybrid_search_oka

# 定義 100 個攝影專屬與頻道熱門關鍵字測試庫
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

def run_100_keywords_audit():
    print("=" * 80, flush=True)
    print(f"🧪 啟動全頻道 100 個攝影關鍵字全自動 Audit 檢測 (總測試庫: {len(KEYWORDS_100)} 個)...", flush=True)
    print("=" * 80, flush=True)

    passed_count = 0
    zero_count = 0
    mapping_issues = 0

    for idx, kw in enumerate(KEYWORDS_100, 1):
        try:
            res = hybrid_search_oka(kw, top_k=50)
            count = len(res)

            # 檢查 1: 標題是否有殘留未 Mapping 的純英文
            pure_eng = [r['video_title'] for r in res if not any('\u4e00' <= c <= '\u9fa5' for c in r['video_title'])]

            if count == 0:
                print(f"[{idx:03d}/100] ❓ 關鍵字: 「{kw}」 -> 0 筆命中", flush=True)
                zero_count += 1
            else:
                passed_count += 1
                if pure_eng:
                    print(f"[{idx:03d}/100] ⚠️ 關鍵字: 「{kw}」 -> 命中 {count} 筆 | 標題待 Mapping: {pure_eng[0][:25]}...", flush=True)
                    mapping_issues += 1
                else:
                    top_t = res[0]['video_title'][:28]
                    print(f"[{idx:03d}/100] ✅ 關鍵字: 「{kw}」 -> 命中 {count} 筆 | 代表標題: {top_t}...", flush=True)

        except Exception as e:
            print(f"[{idx:03d}/100] ❌ 關鍵字: 「{kw}」 -> 拋出例外: {e}", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f"🎉 Audit 檢測總結:", flush=True)
    print(f"  ✨ 有召回與 Mapping 成功: {passed_count - mapping_issues}/100 個關鍵字", flush=True)
    print(f"  ⚠️ 標題需微調 Mapping: {mapping_issues} 個", flush=True)
    print(f"  ❓ 無命中筆數: {zero_count} 個", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_100_keywords_audit()
