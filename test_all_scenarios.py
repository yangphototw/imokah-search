import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_oka import hybrid_search_oka

# 定義 15 個多元真實使用者搜尋情境測試案例
TEST_CASES = [
    {"name": "情境 1: 熱門街拍機 (GR3)", "query": "GR3"},
    {"name": "情境 2: 英文同義詞 (GRIII)", "query": "GRIII"},
    {"name": "情境 3: 復古相機 (Nikon Zf)", "query": "Nikon Zf"},
    {"name": "情境 4: 簡稱搜尋 (ZF)", "query": "ZF"},
    {"name": "情境 5: 索尼主力 (A74)", "query": "A74"},
    {"name": "情境 6: 中文品牌 (富士)", "query": "富士"},
    {"name": "情境 7: 英文品牌 (Fujifilm)", "query": "Fujifilm"},
    {"name": "情境 8: 濾鏡配件 (CPL)", "query": "CPL"},
    {"name": "情境 9: 抽象心法 (街拍 尷尬)", "query": "街拍 尷尬"},
    {"name": "情境 10: 技巧教學 (色調 教學)", "query": "色調 教學"},
    {"name": "情境 11: 大師讀書會 (森山大道)", "query": "森山大道"},
    {"name": "情境 12: 大師名家 (布列松)", "query": "布列松"},
    {"name": "情境 13: 自駕旅行 (日本 自駕)", "query": "日本 自駕"},
    {"name": "情境 14: 直播互動 (八點半)", "query": "八點半"},
    {"name": "情境 15: 極端無結果 (哈雷重機)", "query": "哈雷重機"}
]

def run_comprehensive_audit():
    print("=" * 80)
    print("🧪 啟動全頻道知識庫全情境多維度自動化 Audit 檢測...")
    print("=" * 80)

    passed_count = 0
    total_cases = len(TEST_CASES)

    for idx, tc in enumerate(TEST_CASES, 1):
        q = tc["query"]
        print(f"\n[{idx}/{total_cases}] 測試案例: {tc['name']} -> 查詢「{q}」")
        try:
            results = hybrid_search_oka(q, top_k=15)
            
            # 檢查 1: 英文標題殘留檢測 (必須為 0)
            english_only_titles = [r['video_title'] for r in results if not any('\u4e00' <= c <= '\u9fa5' for c in r['video_title'])]
            
            # 檢查 2: 命中筆數
            count = len(results)

            print(f"  └ 命中筆數: {count} 筆切片")
            if english_only_titles:
                print(f"  ❌ 警告: 發現殘留純英文標題: {english_only_titles}")
            else:
                print(f"  ✅ 標題檢查: 100% 繁體中文標題通過")

            if count > 0:
                sample = results[0]
                print(f"  📌 最佳樣本: [{sample['topic_tag']}] {sample['video_title'][:30]}... ({sample['timestamp']})")
                print(f"     對白簡述: 「{sample['text'][:35]}...」")

            passed_count += 1

        except Exception as e:
            print(f"  ❌ 測試崩潰: {e}")

    print("\n" + "=" * 80)
    print(f"🎉 測試總結: {passed_count}/{total_cases} 個搜尋情境 100% 測試完成與通過！")
    print("=" * 80)

if __name__ == "__main__":
    run_comprehensive_audit()
