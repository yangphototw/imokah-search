import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_oka import hybrid_search_oka

# 20 個極致跨界/奇葩/冷門複合關鍵字測試庫
WEIRD_COMBOS = [
    "彰化 色調",
    "鹿港 噪點",
    "新埔 ISO",
    "苗栗 人像",
    "肉之呼吸 鏡頭",
    "三峽 底片",
    "加德滿都 CPL",
    "八里 快門",
    "埔里 景深",
    "曼谷 白平衡",
    "谷根千 大三元",
    "法羅群島 防手震", "抓周 富士",
    "颱風天 GR3",
    "老街 對焦",
    "路易莎 長曝", "婚攝 彰化",
    "尷尬 北海道",
    "修圖 鹿港",
    "光影 苗栗"
]

def run_weird_test():
    print("=" * 80, flush=True)
    print("🧪 啟動極致奇葩與跨界複合關鍵字 Audit 檢測 (如: 彰化 色調)...", flush=True)
    print("=" * 80, flush=True)

    for idx, combo in enumerate(WEIRD_COMBOS, 1):
        res = hybrid_search_oka(combo, top_k=10)
        c = len(res)
        print(f"\n[{idx:02d}/20] 🔍 奇葩複合詞：「{combo}」 -> 命中 {c} 筆", flush=True)
        if res:
            for top in res[:2]:
                print(f"  📌 代表影片: [{top['topic_tag']}] {top['video_title']} ({top['timestamp']})", flush=True)
                print(f"     💡 核心摘要: {top['summary']}", flush=True)

    print("\n" + "=" * 80, flush=True)
    print("🎉 奇葩複合關鍵字測試完成！", flush=True)

if __name__ == "__main__":
    run_weird_test()
