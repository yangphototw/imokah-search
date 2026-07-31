import os
import sys
import glob
import json
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
AUDIO_DIR = os.path.join(DATA_DIR, "audio_cache")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")
MAP_FILE = os.path.join(DATA_DIR, "oka_youtube_map.json")
INDEX_FILE = os.path.join(DATA_DIR, "oka_rag_index.json")
DEST_STORAGE_DIR = r"F:\AI_Youtube\MP3"
SNAPSHOT_FILE = os.path.join(DATA_DIR, "oka_progress_snapshot.json")

def get_dir_size_mb(path):
    if not os.path.exists(path):
        return 0.0
    total = 0
    for f in os.listdir(path):
        fp = os.path.join(path, f)
        if os.path.isfile(fp):
            total += os.path.getsize(fp)
    return total / (1024 * 1024)

now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

o_tot = 1038
if os.path.exists(MAP_FILE):
    try:
        o_tot = len(json.load(open(MAP_FILE, encoding='utf-8')))
    except Exception:
        pass

o_cache_files = glob.glob(os.path.join(AUDIO_DIR, "*"))
o_arch_files = glob.glob(os.path.join(DEST_STORAGE_DIR, "Oka_*"))
o_mp3_cnt = len(o_cache_files) + len(o_arch_files)
o_mp3_pct = (o_mp3_cnt / o_tot) * 100 if o_tot > 0 else 0
o_mp3_size_gb = (get_dir_size_mb(AUDIO_DIR) + get_dir_size_mb(DEST_STORAGE_DIR)) / 1024

o_stt_files = glob.glob(os.path.join(TRANSCRIPT_DIR, "*_transcript.json"))
o_stt_cnt = len(o_stt_files)
o_stt_pct = (o_stt_cnt / o_tot) * 100 if o_tot > 0 else 0

o_chunks = 0
if os.path.exists(INDEX_FILE):
    try:
        o_chunks = len(json.load(open(INDEX_FILE, encoding='utf-8')))
    except Exception:
        pass

prev_snap = None
if os.path.exists(SNAPSHOT_FILE):
    try:
        prev_snap = json.load(open(SNAPSHOT_FILE, encoding='utf-8'))
    except Exception:
        pass

current_snap = {
    "timestamp": now_str,
    "stt_cnt": o_stt_cnt,
    "stt_pct": o_stt_pct,
    "chunks": o_chunks
}

diff_stt = (o_stt_cnt - prev_snap['stt_cnt']) if prev_snap else 0
diff_chunks = (o_chunks - prev_snap['chunks']) if prev_snap else 0
last_time_str = prev_snap['timestamp'] if prev_snap else "無紀錄"

print("="*70)
print(f"📊 《我都ok啊》專案進度與 DIFF 增量看板 ({now_str})")
print("="*70)
print(f"🎬 總影片數量: {o_tot} 部")
print(f"  ├─ 📥【階段一：MP3 音訊下載 (Producer)】: {o_mp3_cnt} / {o_tot} 部 ({o_mp3_pct:.1f}%) | 快取: {o_mp3_size_gb:.2f} GB")
print(f"  ├─ ⚡【階段二：語音轉文字檔 (Consumer STT)】: {o_stt_cnt} / {o_tot} 部 ({o_stt_pct:.1f}%)  [DIFF 增量: +{diff_stt} 部]")
print(f"  └─ 📚【階段三：閱讀整理與 RAG 索引】: 已索引 {o_stt_cnt} 部 (提煉 {o_chunks:,} 個對話片段) [DIFF 增量: +{diff_chunks:,} 片段]")
print("-"*70)
print(f"⏱️ 上次快取對照時間：{last_time_str}")
print("="*70)

with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
    json.dump(current_snap, f, ensure_ascii=False, indent=2)
