import os
import sys
import json
import glob
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
MAP_FILE = os.path.join(DATA_DIR, "oka_youtube_map.json")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")

def restore_titles():
    print("=" * 65)
    print("🛠️ 開始將被 YouTube 自動翻譯的英文標題全數還原為正宗繁體中文標題...")
    print("=" * 65)

    if not os.path.exists(MAP_FILE):
        print(f"❌ 找不到 {MAP_FILE}")
        return

    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    restored_count = 0
    total_videos = len(vmap)

    for v_id, info in vmap.items():
        md_file = os.path.join(TRANSCRIPT_DIR, f"{v_id}_transcript.md")
        if os.path.exists(md_file):
            try:
                with open(md_file, "r", encoding="utf-8") as mf:
                    first_line = mf.readline().strip()
                    # 格式: # [v_id] 原始中文標題
                    match = re.search(r'#\s*\[[^\]]+\]\s*(.+)', first_line)
                    if match:
                        orig_title = match.group(1).strip()
                        if orig_title and orig_title != info.get("title"):
                            info["title"] = orig_title
                            restored_count += 1
            except Exception as e:
                pass

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(vmap, f, ensure_ascii=False, indent=2)

    print(f"✅ 成功將 {restored_count} 部影片標題全數還原為繁體中文標題！(總計 {total_videos} 部)")

if __name__ == "__main__":
    restore_titles()
