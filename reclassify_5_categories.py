import json
import os
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_map.json")
PRIVACY_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_privacy.json")
CAT_FILE = os.path.join(OKA_ROOT, "data", "oka_gemini_categories.json")

def reclassify():
    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        vmap = json.load(f)

    privacy_db = {}
    if os.path.exists(PRIVACY_FILE):
        with open(PRIVACY_FILE, 'r', encoding='utf-8') as f:
            privacy_db = json.load(f)

    # 5 大分類字典
    # 1. book (讀書會 - 針對攝影集的介紹)
    # 2. live (直播存檔 - 週三八點半與週三攝影週報)
    # 3. member_review (會員評圖 - 每月會員評圖)
    # 4. gear (器材評測 - 有介紹器材的都算)
    # 5. daily (日常影片 - 外出拍照類型)

    new_cats = {}
    counts = {'book': 0, 'live': 0, 'member_review': 0, 'gear': 0, 'daily': 0}

    # 器材關鍵字 (品牌, 機型, 焦段, 光圈, 評測詞)
    gear_keywords = [
        '相機', '鏡頭', '實測', '評測', '開箱', '選購', '手冊', '濾鏡', '腳架', '相機包', '包款',
        'sony', 'fujifilm', '富士', 'nikon', 'canon', 'ricoh', 'gr', 'gr3', 'gr3x', 'gr4',
        'leica', '徠卡', '銘匠', '適馬', 'sigma', 'tamron', '騰龍', '哈蘇', 'hasselblad',
        'zeiss', '蔡司', 'panasonic', 'fx30', 'fx3', 'a7', 'a7iv', 'a7iv', 'a7r', 'a7c',
        'z8', 'z9', 'z6', 'z6iii', 'zf', 'zfc', 'x100v', 'x100vi', 'x-t5', 'x-e4',
        'f1.4', 'f1.8', 'f2.8', 'f4', 'mm f', 'mm'
    ]

    for vid, meta in vmap.items():
        title = meta.get('title', '')
        t_lower = title.lower()

        # 1. 直播存檔 Priority #1 (週三八點半與週三攝影週報)
        if any(k in t_lower for k in ['週三八點半', '週三攝影週報', '週三攝影周報', '攝影週報', '攝影周報', '會後直播']):
            cat = 'live'

        # 2. 讀書會 (針對攝影集/畫冊/書籍介紹)
        elif any(k in t_lower for k in ['讀書會', '導讀', '攝影集', '畫冊', '作品集', '經典畫冊', '書報']):
            cat = 'book'

        # 3. 會員評圖 (每月會員評圖)
        elif '評圖' in t_lower or ('會員' in t_lower and any(k in t_lower for k in ['作業', '照片', '點評', '獨家'])):
            cat = 'member_review'

        # 4. 器材評測 (有介紹器材、鏡頭、相機的都算)
        elif any(k in t_lower for k in gear_keywords) and not any(k in t_lower for k in ['街拍', '散步', '走進你家鄉', '出國拍攝', '旅拍']):
            cat = 'gear'

        # 5. 日常影片 (外出拍照類型、散步街拍、旅拍人像)
        else:
            cat = 'daily'

        new_cats[vid] = cat
        counts[cat] += 1

    print("=" * 80)
    print("🚀 【五大權威新分類】重新歸類統計結果：")
    print(f"   總影片數: {len(vmap)}")
    print(f"   1. 📸 日常影片 (外出拍照): {counts['daily']} 部")
    print(f"   2. 📷 器材評測 (器材介紹): {counts['gear']} 部")
    print(f"   3. 🎙️ 直播存檔 (八點半與週報): {counts['live']} 部")
    print(f"   4. 👑 會員評圖 (每月評圖): {counts['member_review']} 部")
    print(f"   5. 📚 讀書會   (攝影集介紹): {counts['book']} 部")
    print("=" * 80)

    with open(CAT_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_cats, f, ensure_ascii=False, indent=2)

    print(f"已更新寫入 {CAT_FILE}")

if __name__ == '__main__':
    reclassify()
