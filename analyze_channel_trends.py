import os
import sys
import json
import re
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_map.json")
ENCYCLOPEDIA_FILE = os.path.join(OKA_ROOT, "data", "oka_knowledge_encyclopedia.json")

def analyze():
    with open(ENCYCLOPEDIA_FILE, "r", encoding="utf-8") as f:
        encyclopedia = json.load(f)

    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    print("=" * 70)
    print("📊 【《我都OK啊》全頻道內容與流量熱點深度分析報告】")
    print("=" * 70)

    total_videos = len(vmap)
    print(f"\n全頻道收錄總影片數：{total_videos} 部\n")

    # 1. 主題數量比例分析
    print("1️⃣ 【5 大主題產出比例分析】")
    cat_summary = encyclopedia["metadata"]["category_summary"]
    cats = encyclopedia["categories"]
    for c in cats:
        count = len(c["videos"])
        percentage = (count / total_videos) * 100
        print(f"  - {c['icon']} {c['name']}：{count} 部影片 ({percentage:.1f}%)")

    # 2. 高頻關鍵字 (熱門話題與器材)
    all_titles = [v["title"] for v in vmap.values()]
    
    # 提取品牌與機種
    brands = Counter()
    gear_keywords = ["nikon", "sony", "canon", "ricoh", "gr3", "griii", "zf", "fuji", "fujifilm", "leica", "tamron", "sigma", "x100v", "x100vi", "a7iv", "a7r"]
    
    for t in all_titles:
        tl = t.lower()
        for kw in gear_keywords:
            if kw in tl:
                brands[kw.upper()] += 1

    print("\n2️⃣ 【熱門器材與相機話題榜 Top 10】")
    for brand, count in brands.most_common(10):
        print(f"  🔥 {brand} 相關影片：{count} 部")

    # 3. 影片類型與互動切片數分析
    print("\n3️⃣ 【影片長度與深入探討程度 (Top 長影片與直播系列)】")
    long_episodes = []
    for c in cats:
        for v in c["videos"]:
            if v["segment_count"] > 1000:
                long_episodes.append((v["title"], v["segment_count"], v["url"]))

    long_episodes.sort(key=lambda x: x[1], reverse=True)
    print(f"  長篇幅深談/高資訊量影片 (切片數 > 1,000)：共 {len(long_episodes)} 部")
    for title, count, url in long_episodes[:5]:
        print(f"  - [{count} 切片] {title[:40]}...")

    # 4. 總結流量吸睛密碼
    print("\n4️⃣ 【流量密碼與觀眾喜好總結】")
    print("  ⭐ 流量王牌 A：【熱門相機實測與選購實錄】(Nikon Zf, Ricoh GR3, Sony a7IV)")
    print("     - 理由：剛好搭上大熱門復古機身與口袋街拍機的熱潮，買相機前必看的開箱與實戰指南。")
    print("  ⭐ 流量王牌 B：【觀念心法與解決新手痛點】(街拍尷尬、色調教學、新手第一顆鏡頭)")
    print("     - 理由：打中學攝影者真實遇到的瓶頸與心態焦慮，道慈老師平易近人的建議極具親和力。")
    print("  ⭐ 粉絲黏著度王牌 C：【週三八點半直播與會員評圖】")
    print("     - 理由：長度多在 1~2 小時以上，社群互動感極強，包含大量的即時 Q&A 與延伸彩蛋。")

if __name__ == "__main__":
    analyze()
