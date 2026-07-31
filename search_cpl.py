import json
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

idx_p = r"D:\Gemini_CLI\260726_AIOK\data\oka_rag_index.json"
with open(idx_p, "r", encoding="utf-8") as f:
    data = json.load(f)

keywords = ["cpl", "偏光"]
matches = [
    c for c in data 
    if any(kw in c["text"].lower() for kw in keywords)
]

seen_vids = set()
distinct_matches = []

for c in matches:
    if c['video_id'] not in seen_vids:
        seen_vids.add(c['video_id'])
        distinct_matches.append(c)
        if len(distinct_matches) == 5:
            break

print(f"Total CPL/偏光 matches across database: {len(matches)} segments across {len(seen_vids)} videos.\n")

for idx, c in enumerate(distinct_matches, start=1):
    print(f"[{idx}] 🎬 影片: 《{c['video_title']}》")
    print(f"    ⏱️ 時間點: [{c['timestamp']}]")
    print(f"    💬 逐字稿: 「{c['text']}」")
    print(f"    🔗 直跳連結: {c['url']}\n")
