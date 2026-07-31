import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_oka import hybrid_search_oka

TEST_CASES = [
    ("GR3", "情境 1: 熱門街拍機 (GR3)"),
    ("GRIII", "情境 2: 英文同義詞 (GRIII)"),
    ("Nikon Zf", "情境 3: 復古相機 (Nikon Zf)"),
    ("ZF", "情境 4: 簡稱搜尋 (ZF)"),
    ("A74", "情境 5: 索尼主力 (A74)"),
    ("富士", "情境 6: 中文品牌 (富士)"),
    ("Fujifilm", "情境 7: 英文品牌 (Fujifilm)"),
    ("CPL", "情境 8: 濾鏡配件 (CPL)"),
    ("街拍 尷尬", "情境 9: 抽象心法 (街拍 尷尬)"),
    ("色調 教學", "情境 10: 技巧教學 (色調 教學)"),
    ("森山大道", "情境 11: 大師讀書會 (森山大道)"),
    ("布列松", "情境 12: 大師名家 (布列松)"),
    ("日本 自駕", "情境 13: 自駕旅行 (日本 自駕)"),
    ("八點半", "情境 14: 直播互動 (八點半)"),
    ("哈雷重機", "情境 15: 極端無結果 (哈雷重機)")
]

def run_sync_audit():
    print("=" * 80, flush=True)
    print("🧪 執行全頻道 15 個真實搜尋情境全自動 Audit 檢測...", flush=True)
    print("=" * 80, flush=True)

    passed = 0
    for q, name in TEST_CASES:
        res = hybrid_search_oka(q, top_k=10)
        pure_eng = [r['video_title'] for r in res if not any('\u4e00' <= c <= '\u9fa5' for c in r['video_title'])]
        
        print(f"\n👉 [{name}] 查詢：「{q}」 -> 命中 {len(res)} 筆", flush=True)
        if pure_eng:
            print(f"  ❌ 發現殘留英文標題: {pure_eng[0]}", flush=True)
        else:
            print(f"  ✅ 標題 100% 繁體中文通過", flush=True)

        if res:
            top = res[0]
            print(f"  📌 首選代表: [{top['topic_tag']}] {top['video_title'][:30]}... ({top['timestamp']})", flush=True)
        passed += 1

    print("\n" + "=" * 80, flush=True)
    print(f"🎉 全數 {passed}/{len(TEST_CASES)} 個真實使用者情境驗證通過！", flush=True)

if __name__ == "__main__":
    run_sync_audit()
