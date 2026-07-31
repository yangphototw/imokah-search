import os
import sys
import json
import glob
import re
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
MAP_FILE = os.path.join(DATA_DIR, "oka_youtube_map.json")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")
ENCYCLOPEDIA_FILE = os.path.join(DATA_DIR, "oka_knowledge_encyclopedia.json")
TREE_FILE = os.path.join(DATA_DIR, "oka_knowledge_tree.md")

CATEGORIES_DEF = [
    {
        "id": "cat_1",
        "name": "攝影器材與鏡頭評測",
        "icon": "📷",
        "desc": "包含各品牌相機機身、鏡頭評測、攝影週邊配件開箱與實測分析。",
        "keywords": ["nikon", "canon", "sony", "fujifilm", "fuji", "leica", "ricoh", "panasonic", "sigma", "tamron", "voigtlander", "hasselblad", "dji", "iphone", "zf", "z8", "z6", "griii", "gr3", "a7iv", "a7r", "x100v", "x100vi", "r6", "m11", "鏡頭", "焦段", "35mm", "50mm", "85mm", "24-70", "評測", "開箱", "相機", "機身", "快門", "濾鏡", "腳架", "cpl", "nd", "閃光燈", "麥克風", "畫質", "對焦", "防手震"]
    },
    {
        "id": "cat_2",
        "name": "攝影心法與實戰技巧",
        "icon": "🎨",
        "desc": "涵蓋構圖、光影觀念、色彩調校、修圖工作流與各場景實戰攝影技巧。",
        "keywords": ["觀念", "心法", "新手", "教學", "構圖", "光圈", "快門", "感光度", "iso", "曝光", "調色", "修圖", "lightroom", "photoshop", "lut", "街拍", "人像", "風景", "夜景", "長曝", "色彩", "底片", "風格", "思維", "技巧", "練習", "拍照", "攝影", "光影", "美學", "後製"]
    },
    {
        "id": "cat_3",
        "name": "攝影讀書會與大師導讀",
        "icon": "📚",
        "desc": "攝影經典書籍解讀、知名攝影師作品集導讀與攝影理論探討。",
        "keywords": ["讀書會", "大師", "導讀", "攝影集", "經典", "名作", "攝影師", "森山大道", "荒木經惟", "蜷川實花", "杉本博司", "布列松", "saul leiter", "vivian maier", "ansel adams", "stephen shore", "書籍", "書單", "理論", "作品集"]
    },
    {
        "id": "cat_4",
        "name": "國內外攝影旅行與自駕攻略",
        "icon": "✈️",
        "desc": "海外與在地旅遊攝影紀錄、公路自駕攻略、露營與景點拍攝分享。",
        "keywords": ["旅行", "旅遊", "自駕", "vlog", "公路旅行", "日本", "東京", "京都", "北海道", "沖繩", "冰島", "美國", "歐洲", "泰國", "河口湖", "富士山", "自由行", "自駕遊", "營地", "露營", "露營車", "景點", "行程"]
    },
    {
        "id": "cat_5",
        "name": "創作者生活隨筆與直播 Q&A",
        "icon": "💬",
        "desc": "頻道直播互動、Q&A問答、創作者職涯經驗分享與生活隨筆觀察。",
        "keywords": ["直播", "q&a", "qa", "隨筆", "聊聊", "近況", "問答", "問答集", "創作者", "接案", "商業攝影", "心路歷程", "生活", "心情", "訂閱", "會員", "閒聊", "紀錄", "頻道", "幕後"]
    }
]

def is_member_only_video(title):
    t_lower = title.lower()
    member_keywords = ["會員", "評圖", "獨家", "會後聊聊", "專屬", "贊助"]
    return any(k in t_lower for k in member_keywords)

def classify_video(title, transcript_text):
    text_to_check = (title * 3 + " " + transcript_text[:3000]).lower()
    scores = {cat["id"]: 0 for cat in CATEGORIES_DEF}
    for cat in CATEGORIES_DEF:
        cat_id = cat["id"]
        for kw in cat["keywords"]:
            if kw in text_to_check:
                scores[cat_id] += title.lower().count(kw) * 5 + transcript_text[:3000].lower().count(kw)
    t_lower = title.lower()
    if any(k in t_lower for k in ["q&a", "qa", "直播", "會員", "聊聊"]):
        scores["cat_5"] += 15
    if any(k in t_lower for k in ["讀書會", "導讀", "書單"]):
        scores["cat_3"] += 15
    if any(k in t_lower for k in ["日本", "自駕", "冰島", "旅行"]):
        scores["cat_4"] += 10
    if any(k in t_lower for k in ["評測", "開箱", "鏡頭", "nikon", "canon", "sony", "ricoh", "fuji"]):
        scores["cat_1"] += 10
    best_cat_id = max(scores, key=scores.get)
    if scores[best_cat_id] == 0:
        best_cat_id = "cat_5"
    return best_cat_id

def main():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    cat_map = {cat["id"]: {**cat, "videos": []} for cat in CATEGORIES_DEF}

    for v_id, info in vmap.items():
        title = info.get("title", "")
        url = info.get("url", f"https://www.youtube.com/watch?v={v_id}")
        json_path = os.path.join(TRANSCRIPT_DIR, f"{v_id}_transcript.json")
        
        transcript_text = ""
        segment_count = 0
        sample_quotes = []

        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as tf:
                    segments = json.load(tf)
                    segment_count = len(segments)
                    transcript_text = " ".join([s.get("text", "") for s in segments])
                    for s in segments[:5]:
                        if len(s.get("text", "")) > 10:
                            sample_quotes.append({
                                "timestamp": s.get("timestamp", "00:00"),
                                "text": s.get("text", ""),
                                "url": s.get("url", url)
                            })
                            if len(sample_quotes) >= 3:
                                break
            except Exception:
                pass

        best_cat_id = classify_video(title, transcript_text)
        is_member = is_member_only_video(title)

        video_entry = {
            "id": v_id,
            "title": title,
            "url": url,
            "is_member_only": is_member,
            "segment_count": segment_count,
            "sample_quotes": sample_quotes
        }
        cat_map[best_cat_id]["videos"].append(video_entry)

    encyclopedia_data = {
        "metadata": {
            "title": "《我都OK啊》頻道全主題知識大百科",
            "channel": "@imokahhhh",
            "total_videos": len(vmap),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category_summary": {cat_id: len(cat_data["videos"]) for cat_id, cat_data in cat_map.items()}
        },
        "categories": list(cat_map.values())
    }

    with open(ENCYCLOPEDIA_FILE, "w", encoding="utf-8") as f:
        json.dump(encyclopedia_data, f, ensure_ascii=False, indent=2)

    print("✅ 已更新知識庫 JSON，加入 [is_member_only] 標記！")

if __name__ == "__main__":
    main()
