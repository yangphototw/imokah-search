import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_map.json")
TITLE_ZH_MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_title_zh_mapping.json")
GEMINI_CAT_FILE = os.path.join(OKA_ROOT, "data", "oka_gemini_categories.json")

def build_full_1038_categories():
    vmap = {}
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            vmap = json.load(f)

    zh_map = {}
    if os.path.exists(TITLE_ZH_MAP_FILE):
        with open(TITLE_ZH_MAP_FILE, "r", encoding="utf-8") as f:
            zh_map = json.load(f)

    gemini_cats = {}
    if os.path.exists(GEMINI_CAT_FILE):
        try:
            with open(GEMINI_CAT_FILE, "r", encoding="utf-8") as f:
                gemini_cats = json.load(f)
        except Exception:
            pass

    print(f"📊 目前 Gemini API 已權威裁定 {len(gemini_cats)} 部影片，正在為全頻道 {len(vmap)} 部影片進行全量補充補全...", flush=True)

    for v_id, meta in vmap.items():
        if v_id not in gemini_cats:
            title = zh_map.get(v_id, meta.get("title", "")).lower()

            # 1. 讀書會 (book)
            if any(k in title for k in ["讀書會", "導讀", "書報", "書籍", "經典畫冊", "作品集", "書冊"]):
                gemini_cats[v_id] = "book"
            # 2. 直播精華 (live)
            elif any(k in title for k in ["直播", "週三八點半", "週三攝影", "攝影週報", "週報", "會後直播", "線上討論"]):
                gemini_cats[v_id] = "live"
            # 3. 會員影片 (member)
            elif any(k in title for k in ["會員", "評圖", "獨家", "專屬", "會後"]):
                gemini_cats[v_id] = "member"
            # 4. 日常影片 (regular)
            else:
                gemini_cats[v_id] = "regular"

    with open(GEMINI_CAT_FILE, "w", encoding="utf-8") as f:
        json.dump(gemini_cats, f, ensure_ascii=False, indent=2)

    counts = {"regular": 0, "member": 0, "live": 0, "book": 0}
    for cat in gemini_cats.values():
        if cat in counts: counts[cat] += 1

    print("=" * 80, flush=True)
    print(f"🎉 恭喜！全頻道 {len(gemini_cats)} 部影片已完成 100% 完整覆蓋分類庫！", flush=True)
    print(f"  🎬 日常影片 (regular): {counts['regular']} 部")
    print(f"  👑 會員影片 (member):  {counts['member']} 部")
    print(f"  🎙️ 直播精華 (live):    {counts['live']} 部")
    print(f"  📚 讀書會 (book):      {counts['book']} 部")
    print(f"💾 資料庫已寫入 {GEMINI_CAT_FILE}", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    build_full_1038_categories()
