import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
ENCYCLOPEDIA_FILE = os.path.join(DATA_DIR, "oka_knowledge_encyclopedia.json")

# 擴充更全面的會員影片標籤關鍵字
MEMBER_KEYWORDS = [
    "會員", "評圖", "獨家", "會後聊聊", "專屬", "贊助", "限定", 
    "週三八點半", "週三攝影週報", "直播重播", "直播存檔", 
    "評圖直播", "獨家直播", "評圖紀錄", "會後", "直播備份"
]

def is_member_video(title):
    t_lower = title.lower()
    for kw in MEMBER_KEYWORDS:
        if kw in t_lower:
            return True
    return False

def update_member_badges():
    if not os.path.exists(ENCYCLOPEDIA_FILE):
        print("❌ 找不到百科檔案")
        return

    with open(ENCYCLOPEDIA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    member_count = 0
    public_count = 0

    for cat in data.get("categories", []):
        for v in cat.get("videos", []):
            title = v.get("title", "")
            is_member = is_member_video(title)
            v["is_member_only"] = is_member
            if is_member:
                member_count += 1
            else:
                public_count += 1

    with open(ENCYCLOPEDIA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("✅ 會員影片與公開影片標示數據修正完成！")
    print(f"  🔒 會員獨家/直播/評圖影片：{member_count} 部")
    print(f"  🌐 公開免費影片：{public_count} 部")
    print("=" * 60)

if __name__ == "__main__":
    update_member_badges()
