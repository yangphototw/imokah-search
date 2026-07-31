import urllib.request
import re
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_map.json")
DATES_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_dates.json")

def fetch_date_for_vid(vid):
    url = f'https://www.youtube.com/watch?v={vid}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-TW,zh;q=0.9'
    })
    
    pub_date = ""
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            m = re.search(r'"publishDate":"(\d{4}-\d{2}-\d{2})', html)
            if not m:
                m = re.search(r'"uploadDate":"(\d{4}-\d{2}-\d{2})', html)
            if not m:
                m = re.search(r'itemprop="datePublished" content="(\d{4}-\d{2}-\d{2})', html)
                
            if m:
                pub_date = m.group(1)
    except Exception:
        pass

    return vid, pub_date

def fetch_all_dates():
    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        vmap = json.load(f)

    existing_dates = {}
    if os.path.exists(DATES_FILE):
        try:
            with open(DATES_FILE, 'r', encoding='utf-8') as f:
                existing_dates = json.load(f)
        except Exception:
            pass

    total = len(vmap)
    vids_to_check = [vid for vid in vmap.keys() if vid not in existing_dates or not existing_dates[vid]]
    print(f"🚀 開始向 YouTube 抓取全頻道 {len(vids_to_check)} 部影片的發布日期...")

    results = dict(existing_dates)
    completed = total - len(vids_to_check)

    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_vid = {executor.submit(fetch_date_for_vid, vid): vid for vid in vids_to_check}
        for future in as_completed(future_to_vid):
            vid, date_str = future.result()
            results[vid] = date_str
            completed += 1
            if completed % 50 == 0 or completed == total:
                print(f"進度: [{completed}/{total}] 完成...")

    with open(DATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    found_count = sum(1 for d in results.values() if d)
    print("=" * 80)
    print(f"✅ 全頻道 YouTube 發布日期同步完成！")
    print(f"   - 成功取得日期: {found_count} / {total} 部影片")
    print("=" * 80)

if __name__ == '__main__':
    fetch_all_dates()
