import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
MAP_FILE = os.path.join(DATA_DIR, "oka_youtube_map.json")
ENCYCLOPEDIA_FILE = os.path.join(DATA_DIR, "oka_knowledge_encyclopedia.json")

# 精確視訊 ID 到繁體中文標題對照表
EXACT_TITLE_MAP = {
    "Ily62NUBfGg": "Sony a7IV 實拍體驗！新竹一天去哪玩？上班族一日輕旅行好去處！#A74 #波光市集 #雲夢山丘 #南寮漁港",
    "4M8UAV-XSrY": "「攝影讀書會 EP. 24」荒謬的是作品還是這個世界？｜ The Last Resort｜Martin Parr",
    "SAfD1K2Pt0U": "Nikon Zf 鏡頭這樣搭！原廠鏡頭推薦，轉接鏡頭方案與實測一次分享！顏值性能全都要！",
    "75afsR3Tzfg": "相機顏值天花板 復古外觀新世代性能 - Nikon Zf 登場",
    "TcjxOMfSF_k": "人像/婚禮/街拍，一鏡到位 Tamron 17-28mm"
}

def fix_exact():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    for v_id, title in EXACT_TITLE_MAP.items():
        if v_id in vmap:
            vmap[v_id]["title"] = title

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(vmap, f, ensure_ascii=False, indent=2)

    if os.path.exists(ENCYCLOPEDIA_FILE):
        with open(ENCYCLOPEDIA_FILE, "r", encoding="utf-8") as f:
            enc = json.load(f)
        for cat in enc.get("categories", []):
            for v in cat.get("videos", []):
                if v["id"] in EXACT_TITLE_MAP:
                    v["title"] = EXACT_TITLE_MAP[v["id"]]
        with open(ENCYCLOPEDIA_FILE, "w", encoding="utf-8") as f:
            json.dump(enc, f, ensure_ascii=False, indent=2)

    print("✅ 已精確更正 SONY A7IV 實拍體驗等影片為 100% 正宗繁體中文標題！")

if __name__ == "__main__":
    fix_exact()
