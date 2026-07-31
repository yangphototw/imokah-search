import sys
import yt_dlp

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

test_video = "https://www.youtube.com/watch?v=T5Pu5B2_tEc"
cookie_path = r"D:\Gemini_CLI\260726_AIOK\Cookie\www.youtube.com_cookies.txt"

print("測試使用 player_client=['android', 'web'] 下載 YouTube 音訊...")

ydl_opts = {
    'cookiefile': cookie_path,
    'format': 'ba/b',
    'outtmpl': 'test_audio.%(ext)s',
    'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    'quiet': False
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([test_video])
    print("✅ 成功下載音訊！")
except Exception as e:
    print(f"❌ 失敗: {e}")
