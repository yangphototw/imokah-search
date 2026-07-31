import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_map.json")
RAG_INDEX = os.path.join(OKA_ROOT, "data", "oka_rag_index.json")

def fix_all_rag_titles():
    print("=" * 70)
    print("🧹 全量清洗與反向綁定 oka_rag_index.json 中的 1.3M 個標題切片...")
    print("=" * 70)

    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    if os.path.exists(RAG_INDEX):
        with open(RAG_INDEX, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        fixed = 0
        for c in chunks:
            url = c.get("url", "")
            if "v=" in url:
                vid = url.split("v=")[1].split("&")[0]
                if vid in vmap:
                    clean_t = vmap[vid]["title"]
                    if c.get("video_title") != clean_t:
                        c["video_title"] = clean_t
                        fixed += 1

        with open(RAG_INDEX, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        print(f"✅ 完成！共強制修復了 {fixed:,} 個 RAG 對白切片中的影片標題Mapping！")

if __name__ == "__main__":
    fix_all_rag_titles()
