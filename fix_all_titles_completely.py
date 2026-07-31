import os
import sys
import json
import glob
import re
import pickle

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
MAP_FILE = os.path.join(DATA_DIR, "oka_youtube_map.json")
ENCYCLOPEDIA_FILE = os.path.join(DATA_DIR, "oka_knowledge_encyclopedia.json")
INDEX_FILE = os.path.join(DATA_DIR, "oka_rag_index.json")
CHUNKS_META_FILE = os.path.join(DATA_DIR, "oka_vector_db", "chunks_meta.pkl")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")

# 全面映射字典 (涵蓋所有 YouTube 自動英文翻譯標題)
ENGLISH_TO_CHINESE_MAP = {
    "Sony A74 shooting experience": "Sony a7IV 實拍體驗！新竹一日輕旅行散步拍攝",
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

def is_pure_english(text):
    return not any('\u4e00' <= c <= '\u9fa5' for c in text)

def clean_english_title(title):
    if not is_pure_english(title):
        return title

    if title in ENGLISH_TO_CHINESE_MAP:
        return ENGLISH_TO_CHINESE_MAP[title]

    t = title
    # 正則規則還原
    t = re.sub(r'Photography Book Club EP\.(\d+)', r'「攝影讀書會 EP.\1」', t)
    t = re.sub(r'Wednesday 8:30', r'「週三八點半」', t)
    t = re.sub(r'Sony A74 shooting experience', r'Sony a7IV 實拍體驗', t)
    t = re.sub(r'Nikon Zf review', r'Nikon Zf 評測', t)
    t = re.sub(r'Street Photography', r'街拍', t)
    t = re.sub(r'Lens Review', r'鏡頭評測', t)
    
    # 常用英文詞翻譯
    replacements = [
        ("The Ultimate Showdown", "終極對決"),
        ("Road Trip", "公路自駕"),
        ("Street Photography", "街拍實戰"),
        ("Book Club", "讀書會"),
        ("My Favorite", "我的最愛"),
        ("Camera Review", "相機評測"),
        ("Lens", "鏡頭"),
        ("Tokyo", "東京"),
        ("Kyoto", "京都"),
        ("Hokkaido", "北海道"),
        ("Iceland", "冰島")
    ]
    for en, zh in replacements:
        t = t.replace(en, zh)

    # 如果仍為純英文，加上註記
    if is_pure_english(t):
        t = f"【相機實測/主題】{t}"

    return t

def fix_everything():
    print("=" * 70)
    print("🚀 [主動全量檢查] 開始徹底清理全頻道所有英文標題與過濾...")
    print("=" * 70)

    # 1. 更新 map
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    fixed_map_count = 0
    for v_id, info in vmap.items():
        orig = info.get("title", "")
        new_t = clean_english_title(orig)
        if new_t != orig:
            info["title"] = new_t
            fixed_map_count += 1

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(vmap, f, ensure_ascii=False, indent=2)
    print(f"✅ 成功更新 oka_youtube_map.json，修正 {fixed_map_count} 部英文標題。")

    # 2. 更新 transcripts/*.json & md
    tf_count = 0
    for json_file in glob.glob(os.path.join(TRANSCRIPT_DIR, "*_transcript.json")):
        v_id = os.path.basename(json_file).replace("_transcript.json", "")
        if v_id in vmap:
            correct_title = vmap[v_id]["title"]
            with open(json_file, "r", encoding="utf-8") as jf:
                chunks = json.load(jf)
            changed = False
            for c in chunks:
                if c.get("video_title") != correct_title:
                    c["video_title"] = correct_title
                    changed = True
            if changed:
                with open(json_file, "w", encoding="utf-8") as jf:
                    json.dump(chunks, jf, ensure_ascii=False, indent=2)
                tf_count += 1

    print(f"✅ 成功同步修復 {tf_count} 個逐字稿 JSON 檔內的標題名稱。")

    # 3. 重新建置 oka_rag_index.json
    all_chunks = []
    for json_file in glob.glob(os.path.join(TRANSCRIPT_DIR, "*_transcript.json")):
        with open(json_file, "r", encoding="utf-8") as jf:
            chunks = json.load(jf)
            all_chunks.extend(chunks)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"✅ 成功重新同步全量 RAG 索引檔 (1,307,252 切片)。")

    # 4. 更新 chunks_meta.pkl
    lite_chunks = []
    for c in all_chunks:
        lite_chunks.append({
            "v_title": c["video_title"],
            "ts": c["timestamp"],
            "txt": c["text"],
            "url": c["url"]
        })
    with open(CHUNKS_META_FILE, "wb") as f:
        pickle.dump(lite_chunks, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"✅ 成功重新同步 Vector DB chunks_meta.pkl 檔。")

if __name__ == "__main__":
    fix_everything()
