import os
import sys
import io
import json
import re
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
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")
MAP_FILE = os.path.join(DATA_DIR, "oka_youtube_map.json")
INDEX_FILE = os.path.join(DATA_DIR, "oka_rag_index.json")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

def find_cookie_file():
    candidates = [
        os.path.join(OKA_ROOT, "Cookie", "www.youtube.com_cookies.txt"),
        os.path.join(OKA_ROOT, "Cookie", "cookies.txt"),
        os.path.join(OKA_ROOT, "cookies.txt")
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def fetch_oka_video_list():
    all_urls = [
        "https://www.youtube.com/@imokahhhh/videos",
        "https://www.youtube.com/@imokahhhh/shorts",
        "https://www.youtube.com/@imokahhhh/streams",
        "https://www.youtube.com/@imokahhhh/playlists"
    ]
    
    print("="*65)
    print(f"🎬 [我都ok啊 獨立專案] 開始全頻道深度掃描...")
    print("="*65)
    
    cookie_path = find_cookie_file()
    
    ydl_opts = {
        'extract_flat': True,
        'playlistend': 2000,
        'quiet': True,
        'ignoreerrors': True
    }
    
    if cookie_path and os.path.exists(cookie_path):
        print(f"🔑 成功加載會員 Cookie 憑證檔：{cookie_path}")
        ydl_opts['cookiefile'] = cookie_path

    all_videos = {}
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in all_urls:
            print(f"正在掃描分頁: {url}")
            try:
                info = ydl.extract_info(url, download=False)
                if info and 'entries' in info:
                    added = 0
                    for entry in info['entries']:
                        if entry and entry.get("id"):
                            v_id = entry.get("id")
                            title = entry.get("title", "")
                            if len(v_id) == 11 and not v_id.startswith("PL"):
                                if v_id not in all_videos:
                                    all_videos[v_id] = {
                                        "id": v_id,
                                        "title": title,
                                        "url": f"https://www.youtube.com/watch?v={v_id}"
                                    }
                                    added += 1
                    print(f"  └ 成功新增 {added} 部獨立影片/紀錄")
            except Exception as e:
                print(f"  └ [提示] 掃描 {url}: {e}")
                
    print(f"\n🎉 成功解鎖《我都ok啊》頻道共 {len(all_videos)} 部獨立影片（包含所有公開與會員專屬影片）！")
    
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(all_videos, f, ensure_ascii=False, indent=2)
        
    return all_videos

def format_timestamp(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def run_whisper_oka(audio_path, model_size="small"):
    from faster_whisper import WhisperModel
    try:
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        segments, info = model.transcribe(audio_path, language="zh", vad_filter=True)
        return list(segments), info
    except Exception as e:
        print(f"  ⚙️ [GPU 不可用，無縫切換 CPU 4進程]: {e}")
        model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4)
        segments, info = model.transcribe(audio_path, language="zh", vad_filter=True)
        return list(segments), info

def process_oka_transcripts():
    if not os.path.exists(MAP_FILE):
        print("未找到影片對照檔。")
        return

    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    cookie_path = find_cookie_file()

    print(f"\n⚡ 啟動高效雙階段轉譯《我都ok啊》頻道...")

    all_chunks = []
    total_vids = len(vmap)
    processed = 0
    
    for v_id, info in vmap.items():
        processed += 1
        title = info['title']
        
        json_path = os.path.join(TRANSCRIPT_DIR, f"{v_id}_transcript.json")
        md_path = os.path.join(TRANSCRIPT_DIR, f"{v_id}_transcript.md")
        audio_path = os.path.join(AUDIO_DIR, f"{v_id}.mp3")

        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
                all_chunks.extend(chunks)
            continue

        print(f"\n[{processed}/{total_vids}] 正在處理：[{v_id}] {title}...")
        
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
                ydl.download([info['url']])
        except Exception as e:
            print(f"❌ 下載失敗 [{v_id}]: {e}")
            continue

        if not os.path.exists(audio_path):
            candidates = glob.glob(os.path.join(AUDIO_DIR, f"{v_id}.*"))
            if candidates:
                audio_path = candidates[0]
            else:
                print(f"❌ 無法取得音訊檔 [{v_id}]")
                continue

        try:
            segments, s_info = run_whisper_oka(audio_path, model_size="small")
            
            chunks = []
            md_lines = [f"# [{v_id}] {title}\n", f"影片網址: {info['url']}\n\n## 語音逐字稿與時間戳記\n"]
            
            for seg in segments:
                start_str = format_timestamp(seg.start)
                yt_jump_link = f"https://www.youtube.com/watch?v={v_id}&t={int(seg.start)}s"
                
                chunk_obj = {
                    "source": "我都ok啊",
                    "video_id": v_id,
                    "video_title": title,
                    "start": seg.start,
                    "timestamp": start_str,
                    "text": seg.text.strip(),
                    "url": yt_jump_link
                }
                chunks.append(chunk_obj)
                all_chunks.append(chunk_obj)
                md_lines.append(f"- **[{start_str}]** [{seg.text.strip()}]({yt_jump_link})")
                
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))
                
            print(f"✅ [{v_id}] 轉譯完成！生成帶時間戳直跳網址。")
        except Exception as e:
            print(f"❌ 轉譯失敗 [{v_id}]: {e}")

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"\n🎉 《我都ok啊》獨立專案全影片 RAG 索引建置完成！共索引 {len(all_chunks)} 個時間戳記片段。")

if __name__ == "__main__":
    fetch_oka_video_list()
    process_oka_transcripts()
