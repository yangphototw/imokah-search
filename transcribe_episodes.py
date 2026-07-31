import os
import sys
import io
import json
import ctypes

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

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

def format_timestamp(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def transcribe_audio_file(audio_path, video_id, title, model_size="small"):
    from faster_whisper import WhisperModel

    try:
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        segments, info = model.transcribe(
            audio_path, 
            language="zh", 
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        seg_list = list(segments)
        print(f"⚡ [RTX 3070 CUDA GPU 加速成功]", flush=True)
    except Exception as e:
        print(f"⚙️ [GPU CUDA 不可用 ({e})，切換至 CPU 4進程]:", flush=True)
        model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4)
        segments, info = model.transcribe(
            audio_path, 
            language="zh", 
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        seg_list = list(segments)

    chunk_list = []
    md_lines = [f"# [{video_id}] {title}\n", "## 語音逐字稿與時間戳記\n"]

    for segment in seg_list:
        start_str = format_timestamp(segment.start)
        end_str = format_timestamp(segment.end)
        yt_jump_link = f"https://www.youtube.com/watch?v={video_id}&t={int(segment.start)}s"
        text = segment.text.strip()

        chunk_list.append({
            "source": "我都ok啊",
            "video_id": video_id,
            "video_title": title,
            "start": segment.start,
            "end": segment.end,
            "timestamp": start_str,
            "text": text,
            "url": yt_jump_link
        })
        md_lines.append(f"- **[{start_str} - {end_str}]** [{text}]({yt_jump_link})")

    return chunk_list, md_lines
