import os
import sys
import json
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
MAP_FILE = os.path.join(DATA_DIR, "oka_youtube_map.json")
ENCYCLOPEDIA_FILE = os.path.join(DATA_DIR, "oka_knowledge_encyclopedia.json")
CHUNKS_META_FILE = os.path.join(DATA_DIR, "oka_vector_db", "chunks_meta.pkl")

# 常見 YouTube 自動翻譯標題的中英對照地圖
TITLE_TRANSLATION_MAP = {
    "The Whole City Is One Big Museum | Kathmandu, a Street Photography Mecca": "「整個城市都是博物館」加德滿都，街拍聖地",
    "Photography Book Club EP.33 | Record No. 28: The Everyday Is Most Worth Recording | Daido Moriyama": "「攝影讀書會 EP.33」記錄 No. 28 最值得記錄的是日常｜森山大道",
    "The Four of Us Went to See a Stage Play... | The Peach Blossom Land | Stan Lai": "我們四個跑去看舞台劇... 桃花源｜賴聲川",
    "A Grip! I Added a Grip! Re-Reviewing the Nikon Zf Two Years Later": "手把！我加了手把！兩年後重評 Nikon Zf",
    "World's 2nd Best City to Travel To! What Does Morioka Actually Have?": "世界第二宜居旅遊城市！盛岡到底有什麼？",
    "Better Experience with a Grip! A Camera with Character and StyleUSigma BFUft. Tichead TILTA Filters": "加手把手感大提升！有個性與風格的相機 - Sigma BF",
    "We Adopted a Plum Tree...": "我們領養了一棵梅花樹...",
    "Into the Land of SnowUAn Easy Half-Day Road Trip Around Sapporo!": "駛入雪國 - 札幌周邊半日輕鬆自駕公路旅行！",
    "28mm or 35mm, How to Choose? The Ultimate Showdown of Angle of View and Depth of Field": "28mm 還是 35mm 怎麼選？視角與景深的終極對決",
    "Flew Halfway Across the World for a Single BirdUBucket-List Dream: The Faroe Islands": "為了看一隻鳥飛了大半個地球 - 人生夢幻清單：法羅群島"
}

def translate_title(title):
    if not any('\u4e00' <= c <= '\u9fa5' for c in title):
        # 尋找直接對照
        if title in TITLE_TRANSLATION_MAP:
            return TITLE_TRANSLATION_MAP[title]
        # 常規模式取代
        t = title
        t = t.replace("Photography Book Club", "「攝影讀書會」")
        t = t.replace("Wednesday 8:30", "「週三八點半」")
        t = t.replace("Street Photography", "街拍")
        t = t.replace("Nikon Zf", "Nikon Zf")
        t = t.replace("Ricoh GR3", "Ricoh GR3")
        t = t.replace("Sony", "Sony")
        t = t.replace("Fuji", "富士")
        t = t.replace("Lens Review", "鏡頭評测")
        t = t.replace("Vlog", "Vlog")
        return t
    return title

def process():
    print("=" * 65)
    print("🛠️ 開始清理與轉譯全頻道 101 部英文標題為標準繁體中文標題...")
    print("=" * 65)

    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    converted = 0
    for v_id, info in vmap.items():
        orig = info.get("title", "")
        new_t = translate_title(orig)
        if new_t != orig:
            info["title"] = new_t
            converted += 1

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(vmap, f, ensure_ascii=False, indent=2)

    # 同步更新 Encyclopedia
    if os.path.exists(ENCYCLOPEDIA_FILE):
        with open(ENCYCLOPEDIA_FILE, "r", encoding="utf-8") as f:
            enc = json.load(f)
        for cat in enc.get("categories", []):
            for v in cat.get("videos", []):
                if v["id"] in vmap:
                    v["title"] = vmap[v["id"]]["title"]
        with open(ENCYCLOPEDIA_FILE, "w", encoding="utf-8") as f:
            json.dump(enc, f, ensure_ascii=False, indent=2)

    print(f"✅ 成功將 {converted} 部英文翻譯標題轉譯為正宗繁體中文標題！")

if __name__ == "__main__":
    process()
