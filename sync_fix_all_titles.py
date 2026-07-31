import os
import sys
import json
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

def is_pure_english(text):
    return not any('\u4e00' <= c <= '\u9fa5' for c in text)

def clean_title(t):
    if not is_pure_english(t):
        return t
    if "Sony A74 shooting experience" in t:
        return "Sony a7IV 實拍體驗！新竹一日輕旅行散步拍攝"
    if "Kathmandu" in t:
        return "「整個城市都是博物館」加德滿都，街拍聖地"
    if "Daido Moriyama" in t:
        return "「攝影讀書會 EP.33」記錄 No. 28 最值得記錄的是日常｜森山大道"
    if "Peach Blossom Land" in t:
        return "我們四個跑去看舞台劇... 桃花源｜賴聲川"
    if "Nikon Zf" in t:
        return "手把！我加了手把！兩年後重評 Nikon Zf"
    if "Morioka" in t:
        return "世界第二宜居旅遊城市！盛岡到底有什麼？"
    if "Sigma BF" in t:
        return "加手把手感大提升！有個性與風格的相機 - Sigma BF"
    if "Plum Tree" in t:
        return "我們領養了一棵梅花樹..."
    if "Sapporo" in t:
        return "駛入雪國 - 札幌周邊半日輕鬆自駕公路旅行！"
    if "28mm or 35mm" in t:
        return "28mm 還是 35mm 怎麼選？視角與景深的終極對決"
    if "Faroe Islands" in t:
        return "為了看一隻鳥飛了大半個地球 - 人生夢幻清單：法羅群島"
    
    t = re.sub(r'Photography Book Club EP\.(\d+)', r'「攝影讀書會 EP.\1」', t)
    t = re.sub(r'Wednesday 8:30', r'「週三八點半」', t)
    t = t.replace("Lens Review", "鏡頭評測").replace("Street Photography", "街拍實戰")
    return t

def run():
    print("="*60, flush=True)
    print("🛠️ 開始修正 map 與 encyclopedia 標題...", flush=True)
    print("="*60, flush=True)

    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    fixed = 0
    for v_id, info in vmap.items():
        orig = info.get("title", "")
        new_t = clean_title(orig)
        if new_t != orig:
            info["title"] = new_t
            fixed += 1

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(vmap, f, ensure_ascii=False, indent=2)

    print(f"✅ 修正 {fixed} 部標題！", flush=True)

    # 重新運行 build_knowledge_base 與 fix_member_badges
    os.system(f'"{sys.executable}" build_knowledge_base.py')
    os.system(f'"{sys.executable}" fix_member_badges.py')
    print("🎉 標題與會員標籤同步完成！", flush=True)

if __name__ == "__main__":
    run()
