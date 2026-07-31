import os
import sys
import io
import json
import glob
import time
import shutil
import ctypes
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Target storage for finished MP3s/audios
DEST_STORAGE_DIR = r"F:\AI_Youtube\MP3"
os.makedirs(DEST_STORAGE_DIR, exist_ok=True)

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# Dynamic CUDA DLL binding including user site-packages
try:
    import site
    sp_list = site.getsitepackages()
    user_sp = site.getusersitepackages()
    if user_sp not in sp_list:
        sp_list.append(user_sp)
        
    for sp in sp_list:
        for sub in ["cublas", "cudnn", "cuda_nvrtc"]:
            bin_path = os.path.join(sp, "nvidia", sub, "bin")
            if os.path.exists(bin_path):
                os.add_dll_directory(bin_path)
                os.environ["PATH"] = bin_path + os.pathsep + os.environ["PATH"]
                for f in os.listdir(bin_path):
                    if f.endswith(".dll"):
                        try:
                            ctypes.cdll.LoadLibrary(os.path.join(bin_path, f))
                        except Exception:
                            pass
except Exception:
    pass

from batch_rag_indexer import build_rag_index
from transcribe_episodes import format_timestamp

def run_whisper_oka(audio_path, model_size="small"):
    from faster_whisper import WhisperModel
    try:
        model = WhisperModel(model_size, device="cuda", compute_type="float16", cpu_threads=2)
        segments, info = model.transcribe(audio_path, language="zh", vad_filter=True)
        seg_list = list(segments)
        print(f"⚡ [RTX 3070 CUDA GPU 爆速轉譯成功]", flush=True)
        return seg_list, info
    except Exception as e:
        print(f"  ⚙️ [GPU CUDA 不可用 ({e})，無縫切換 CPU 4進程]:", flush=True)
        model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4)
        segments, info = model.transcribe(audio_path, language="zh", vad_filter=True)
        return list(segments), info

def archive_finished_oka_audio(audio_path, v_id):
    if not os.path.exists(audio_path):
        return
    ext = os.path.splitext(audio_path)[1]
    dest_path = os.path.join(DEST_STORAGE_DIR, f"Oka_{v_id}{ext}")
    try:
        if audio_path != dest_path:
            shutil.move(audio_path, dest_path)
            print(f"📦 [自動歸檔] 已將《我都ok啊》[{v_id}] 音訊檔移動至：{dest_path}", flush=True)
    except Exception as e:
        print(f"⚠️ 歸檔 [{v_id}] 音訊時發生錯誤: {e}", flush=True)

def process_cached_oka_video(v_id, title, url):
    json_path = os.path.join(TRANSCRIPT_DIR, f"{v_id}_transcript.json")
    md_path = os.path.join(TRANSCRIPT_DIR, f"{v_id}_transcript.md")
    
    if os.path.exists(json_path):
        return (v_id, True, "已存在逐字稿")

    audio_path = os.path.join(AUDIO_DIR, f"{v_id}.mp3")
    if not os.path.exists(audio_path):
        candidates = glob.glob(os.path.join(AUDIO_DIR, f"{v_id}.*"))
        if candidates:
            audio_path = candidates[0]
        else:
            dest_candidates = glob.glob(os.path.join(DEST_STORAGE_DIR, f"Oka_{v_id}.*"))
            if dest_candidates:
                audio_path = dest_candidates[0]
            else:
                return (v_id, False, f"未找到音訊快取檔 [{v_id}]")

    try:
        segments, s_info = run_whisper_oka(audio_path, model_size="small")
        chunks = []
        md_lines = [f"# [{v_id}] {title}\n", f"影片網址: {url}\n\n## 語音逐字稿與時間戳記\n"]
        
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
            md_lines.append(f"- **[{start_str}]** [{seg.text.strip()}]({yt_jump_link})")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        archive_finished_oka_audio(audio_path, v_id)
        return (v_id, True, "成功")
    except Exception as e:
        return (v_id, False, str(e))

def run_dynamic_oka_watcher(max_workers=1):
    if not os.path.exists(MAP_FILE):
        print(f"未找到影片對照檔 {MAP_FILE}", flush=True)
        return

    with open(MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    total_vids = len(vmap)

    print("="*65, flush=True)
    print(f"🧪 [《我都ok啊》單執行緒 1 Thread 實測] 啟動！分配 {max_workers} Worker 零 Context Switch 測試...", flush=True)
    print(f"歸檔資料夾: {DEST_STORAGE_DIR}")
    print(f"總目標影片數: {total_vids} 部")
    print("="*65, flush=True)

    in_progress = set()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        active_futures = {}

        while True:
            # 1. Count completed transcripts
            completed_count = len([
                v_id for v_id in vmap 
                if os.path.exists(os.path.join(TRANSCRIPT_DIR, f"{v_id}_transcript.json"))
            ])

            if completed_count >= total_vids:
                print(f"\n🎉 全數 {total_vids} 部影片已完成轉譯與 RAG 索引化！動態監聽器平續退出。", flush=True)
                break

            # 2. Find newly downloaded audio files (.webm, .m4a, .mp3)
            candidate_vids = []
            for v_id, info in vmap.items():
                if v_id in in_progress:
                    continue
                if os.path.exists(os.path.join(TRANSCRIPT_DIR, f"{v_id}_transcript.json")):
                    continue
                    
                candidates = glob.glob(os.path.join(AUDIO_DIR, f"{v_id}.*"))
                if candidates and os.path.getsize(candidates[0]) > 100 * 1024:
                    candidate_vids.append((v_id, info['title'], info['url']))

            # 3. Dispatch available workers up to max_workers limit
            available_slots = max_workers - len(active_futures)

            if available_slots > 0 and candidate_vids:
                for v_id, title, url in candidate_vids[:available_slots]:
                    in_progress.add(v_id)
                    print(f"🚀 [派發 Thread Worker] 發現新音訊：[{v_id}] {title}，開始轉譯...", flush=True)
                    future = executor.submit(process_cached_oka_video, v_id, title, url)
                    active_futures[future] = v_id

            # 4. Check completed futures
            done_futures = [f for f in active_futures if f.done()]
            for f in done_futures:
                v_id = active_futures.pop(f)
                in_progress.remove(v_id)
                try:
                    v_id_res, success, msg = f.result()
                    current_done = len([
                        vid for vid in vmap 
                        if os.path.exists(os.path.join(TRANSCRIPT_DIR, f"{vid}_transcript.json"))
                    ])
                    pct = (current_done / total_vids) * 100
                    if success and msg == "成功":
                        print(f"✅ [進度 {current_done}/{total_vids} ({pct:.1f}%)] [{v_id}] 轉譯完成並歸檔！", flush=True)
                        build_rag_index()
                    elif msg != "已存在逐字稿":
                        print(f"⚠️ [{v_id}] 處理狀態: {msg}", flush=True)
                except Exception as e:
                    print(f"❌ [{v_id}] 發生異常: {e}", flush=True)

            time.sleep(1)

    build_rag_index()

if __name__ == "__main__":
    run_dynamic_oka_watcher(max_workers=2)
