"""Idempotent local updater for new YouTube videos.

Heavy work stays on the owner's PC (where GPU and cookies live); Vercel only
receives the small static public/ output after all validation passes.
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp

from incremental_static_index import update_for_new_videos
from build_public_paragraph_index import update_for_videos as update_paragraphs_for_videos

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MAP_FILE = DATA / "oka_youtube_map.json"
STATE_FILE = DATA / "update_state.json"
AUDIO_DIR = DATA / "audio_cache"
TRANSCRIPT_DIR = DATA / "transcripts"
CHANNEL_PAGES = (
    "https://www.youtube.com/@imokahhhh/videos",
    "https://www.youtube.com/@imokahhhh/shorts",
    "https://www.youtube.com/@imokahhhh/streams",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json_write(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def cookie_file() -> Path | None:
    for path in (ROOT / "Cookie" / "www.youtube.com_cookies.txt", ROOT / "Cookie" / "cookies.txt", ROOT / "cookies.txt"):
        if path.is_file():
            return path
    return None


def discovery_options() -> dict:
    options = {
        "extract_flat": True,
        "playlistend": 2000,
        "quiet": True,
        "ignoreerrors": True,
        "extractor_args": {"youtube": {"lang": ["zh-TW", "zh-Hant"]}},
    }
    if cookie := cookie_file():
        options["cookiefile"] = str(cookie)
    return options


def discover_videos() -> dict[str, dict]:
    videos = {}
    with yt_dlp.YoutubeDL(discovery_options()) as ydl:
        for page in CHANNEL_PAGES:
            info = ydl.extract_info(page, download=False)
            for entry in (info or {}).get("entries", []):
                video_id = (entry or {}).get("id")
                if not video_id or len(video_id) != 11 or video_id.startswith("PL"):
                    continue
                videos.setdefault(video_id, {
                    "id": video_id,
                    "title": entry.get("title", ""),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "upload_date": entry.get("upload_date", ""),
                })
    return videos


def make_transcriber(model_size: str):
    from faster_whisper import WhisperModel

    try:
        return WhisperModel(model_size, device="cuda", compute_type="float16"), "cuda"
    except Exception as error:
        print(f"GPU unavailable; using CPU int8: {error}", flush=True)
        return WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4), "cpu"


def download_audio(video: dict) -> Path:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    expected = AUDIO_DIR / f"{video['id']}.mp3"
    if expected.exists():
        return expected
    options = {
        "format": "ba/b",
        "outtmpl": str(AUDIO_DIR / f"{video['id']}.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        "js_runtimes": {"node": {}},
        "remote_components": ["ejs:github"],
        "retries": 3,
        "fragment_retries": 3,
        "sleep_interval": 2,
        "max_sleep_interval": 4,
        "quiet": True,
    }
    if cookie := cookie_file():
        options["cookiefile"] = str(cookie)
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([video["url"]])
    if expected.exists():
        return expected
    candidates = list(AUDIO_DIR.glob(f"{video['id']}.*"))
    if not candidates:
        raise FileNotFoundError(f"Audio download missing for {video['id']}")
    return candidates[0]


def transcribe(video: dict, model) -> list[dict]:
    audio = download_audio(video)
    segments, _ = model.transcribe(str(audio), language="zh", vad_filter=True)
    chunks = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        start = round(float(segment.start), 2)
        chunks.append({
            "source": "我都ok啊",
            "video_id": video["id"],
            "video_title": video["title"],
            "start": start,
            "timestamp": f"{int(start // 60):02d}:{int(start % 60):02d}",
            "text": text,
            "url": f"https://www.youtube.com/watch?v={video['id']}&t={int(start)}s",
        })
    if not chunks or sum(len(chunk["text"]) for chunk in chunks) < 40:
        raise ValueError("Transcript quality check failed: too little spoken text")
    return chunks


def save_transcript(video: dict, chunks: list[dict]) -> None:
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    transcript_path = TRANSCRIPT_DIR / f"{video['id']}_transcript.json"
    markdown_path = TRANSCRIPT_DIR / f"{video['id']}_transcript.md"
    temporary = transcript_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(transcript_path)
    lines = [f"# [{video['id']}] {video['title']}", f"影片網址: {video['url']}", "", "## 語音逐字稿與時間戳記"]
    lines.extend(f"- **[{chunk['timestamp']}]** [{chunk['text']}]({chunk['url']})" for chunk in chunks)
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Incrementally update the AIOK static search site")
    parser.add_argument("--dry-run", action="store_true", help="Only report newly discovered videos")
    parser.add_argument("--max-videos", type=int, default=0, help="Process at most this many new videos")
    parser.add_argument("--model", default="small", help="faster-whisper model size")
    args = parser.parse_args()

    existing_map = load_json(MAP_FILE, {})
    state = load_json(STATE_FILE, {"version": 1, "videos": {}})
    discovered = discover_videos()
    new_ids = [video_id for video_id in discovered if not (TRANSCRIPT_DIR / f"{video_id}_transcript.json").exists()]
    new_ids.sort(key=lambda video_id: discovered[video_id].get("upload_date", ""))
    if args.max_videos:
        new_ids = new_ids[:args.max_videos]

    print(f"Discovered {len(discovered)} videos; {len(new_ids)} need transcripts.", flush=True)
    if args.dry_run or not new_ids:
        return 0

    model, device = make_transcriber(args.model)
    print(f"Transcribing on {device}; model loads once for this update.", flush=True)
    completed = []
    for video_id in new_ids:
        video = discovered[video_id]
        record = state.setdefault("videos", {}).setdefault(video_id, {})
        record.update({"title": video["title"], "status": "processing", "updated_at": now()})
        atomic_json_write(STATE_FILE, state)
        try:
            chunks = transcribe(video, model)
            save_transcript(video, chunks)
            existing_map[video_id] = video
            record.update({"status": "transcribed", "segments": len(chunks), "updated_at": now(), "error": ""})
            completed.append(video_id)
            print(f"OK {video_id}: {len(chunks)} segments", flush=True)
        except Exception as error:
            record.update({"status": "failed", "updated_at": now(), "error": str(error)})
            print(f"FAILED {video_id}: {error}", flush=True)
        atomic_json_write(STATE_FILE, state)

    if not completed:
        raise SystemExit("No new transcript passed validation; deployment was not changed")

    atomic_json_write(MAP_FILE, existing_map)
    changed_shards = update_for_new_videos(completed)
    changed_paragraph_shards = update_paragraphs_for_videos(completed)
    for video_id in completed:
        state["videos"][video_id].update({"status": "deployed", "updated_at": now()})
    atomic_json_write(STATE_FILE, state)
    print(
        f"Updated {len(completed)} videos across {changed_shards} search shards "
        f"and {changed_paragraph_shards} paragraph shards.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
