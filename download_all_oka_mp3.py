import os
import sys
import io
import json
import glob
import time
import yt_dlp

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
AUDIO_DIR = os.path.join(DATA_DIR, "audio_cache")
MAP_FILE = os.path.join(DATA_DIR, "oka_youtube_map.json")
COOKIE_FILE = os.path.join(OKA_ROOT, "Cookie", "www.youtube.com_cookies.txt")

os.makedirs(AUDIO_DIR, exist_ok=True)

def find_cookie_file():
    candidates = [
        COOKIE_FILE,
        os.path.join(OKA_ROOT, "Cookie", "cookies.txt"),
        os.path.join(OKA_ROOT, "cookies.txt")
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def download_oka_mp3(v_id, url, title, total_count, current_idx):
    target_path = os.path.join(AUDIO_DIR, f"{v_id}.mp3")
    
    # Check if MP3 already exists and valid size (> 100KB)
    if os.path.exists(target_path) and os.path.getsize(target_path) > 100 * 1024:
        size_mb = os.path.getsize(target_path) / (1024 * 1024)
        pct = (current_idx / total_count) * 100
        print(f"⏩ [{current_idx}/{total_count} ({pct:.1f}%)] [{v_id}] MP3 已存在快取 ({size_mb:.1f} MB)，跳過。", flush=True)
        return True

    print(f"📥 [{current_idx}/{total_count} ({(current_idx/total_count)*100:.1f}%)] 正在下載 [{v_id}] {title}...", flush=True)

    cookie_path = find_cookie_file()

    ydl_opts = {
        'format': 'ba/b',
        'outtmpl': os.path.join(AUDIO_DIR, f"{v_id}.%(ext)s"),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'js_runtimes': {'node': {}},
        'remote_components': ['ejs:github'],
        'sleep_interval': 2,
        'max_sleep_interval': 4,
        'quiet': True,
        'ignoreerrors': True
    }

    if cookie_path and os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(target_path):
            size_mb = os.path.getsize(target_path) / (1024 * 1024)
            print(f"✅ [{v_id}] MP3 下載完成！(大小: {size_mb:.1f} MB)", flush=True)
            return True
        else:
            candidates = glob.glob(os.path.join(AUDIO_DIR, f"{v_id}.*"))
            if candidates:
                print(f"✅ [{v_id}] 音訊檔案準備完成！", flush=True)
                return True
            print(f"❌ [{v_id}] 無法找到產出的音訊檔。", flush=True)
            return False
    except Exception as e:
        print(f"❌ [{v_id}] 下載失敗: {e}", flush=True)
        return False

def main():
    if not os.path.exists(MAP_FILE):
        print(f"未找到影片對照庫 {MAP_FILE}，請先執行全頻道掃描。", flush=True)
        return

    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    total = len(vmap)
    print("="*65, flush=True)
    print(f"📥 [階段一：《我都ok啊》專用 MP3 下載 SCRIPT] 準備下載 {total} 部影片音訊檔")
    print("="*65, flush=True)

    success_count = 0
    for idx, (v_id, info) in enumerate(vmap.items(), start=1):
        res = download_oka_mp3(v_id, info['url'], info['title'], total, idx)
        if res:
            success_count += 1

    print("\n" + "="*65, flush=True)
    print(f"🎉 階段一完成！《我都ok啊》共 {success_count}/{total} 部影片 MP3 下載完畢。", flush=True)
    print("="*65, flush=True)

if __name__ == "__main__":
    main()
