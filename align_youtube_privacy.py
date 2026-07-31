import urllib.request
import re
import json
import time
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_map.json")
PRIVACY_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_privacy.json")

def check_video_privacy(vid):
    url = f'https://www.youtube.com/watch?v={vid}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-TW,zh;q=0.9'
    })
    
    privacy_info = {
        "vid": vid,
        "is_member_only": False,
        "is_unlisted": False,
        "is_private": False,
        "status": "OK",
        "reason": ""
    }
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            m = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});</script>', html)
            if not m:
                m = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});var', html)
                
            if m:
                try:
                    data = json.loads(m.group(1))
                    playability = data.get('playabilityStatus', {})
                    status = playability.get('status', 'OK')
                    reason = playability.get('reason', '')
                    
                    microformat = data.get('microformat', {}).get('playerMicroformatRenderer', {})
                    is_unlisted = microformat.get('isUnlisted', False)
                    
                    privacy_info["status"] = status
                    privacy_info["reason"] = reason
                    privacy_info["is_unlisted"] = is_unlisted
                    
                    if status == "UNPLAYABLE" and ("會員" in reason or "members" in reason.lower()):
                        privacy_info["is_member_only"] = True
                    elif status == "LOGIN_REQUIRED" or "Private" in reason or "私人" in reason:
                        privacy_info["is_private"] = True
                        privacy_info["is_member_only"] = True
                    elif is_unlisted:
                        privacy_info["is_member_only"] = True  # 直播存檔 / 讀書會非公開
                except Exception as e:
                    pass
    except urllib.error.HTTPError as e:
        if e.code == 404:
            privacy_info["is_private"] = True
            privacy_info["is_member_only"] = True
    except Exception as e:
        pass

    return privacy_info

def align_all():
    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        vmap = json.load(f)

    existing_privacy = {}
    if os.path.exists(PRIVACY_FILE):
        try:
            with open(PRIVACY_FILE, 'r', encoding='utf-8') as f:
                existing_privacy = json.load(f)
        except Exception:
            pass

    total = len(vmap)
    print(f"🚀 開始抓取全頻道 {total} 部影片在 YouTube 上的真實權限 (Unlisted / Members Only)...")

    vids_to_check = list(vmap.keys())
    results = dict(existing_privacy)
    completed = len(results)

    # Use ThreadPoolExecutor for fast multi-threaded fetching
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_vid = {executor.submit(check_video_privacy, vid): vid for vid in vids_to_check if vid not in results}
        
        for future in as_completed(future_to_vid):
            info = future.result()
            results[info["vid"]] = info
            completed += 1
            if completed % 50 == 0 or completed == total:
                print(f"进度: [{completed}/{total}] 完成...")

    with open(PRIVACY_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    member_count = sum(1 for v in results.values() if v.get("is_member_only"))
    unlisted_count = sum(1 for v in results.values() if v.get("is_unlisted"))

    print("=" * 80)
    print(f"✅ 全頻道 YouTube 真實權限同步完成！")
    print(f"   - 總影片數: {total}")
    print(f"   - YouTube 實測會員限定/非公開 (Members-Only / Unlisted): {member_count} 部")
    print(f"   - YouTube 實測非公開 (Unlisted): {unlisted_count} 部")
    print("=" * 80)

if __name__ == '__main__':
    align_all()
