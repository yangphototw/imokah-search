import os
import sys
import json
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
# public is the deployable static site.  Keeping the local server on the same
# directory makes local QA match Vercel's zero-function production build.
WEB_DIR = os.path.join(OKA_ROOT, "public")
GEMINI_CAT_FILE = os.path.join(OKA_ROOT, "data", "oka_gemini_categories.json")
PRIVACY_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_privacy.json")
DATES_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_dates.json")

from ai_oka import hybrid_search_oka, get_video_map, get_llm_summaries, get_clean_title, get_title_zh_map
from content_quality import display_summary

def get_youtube_privacy_map():
    if os.path.exists(PRIVACY_FILE):
        try:
            with open(PRIVACY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_youtube_dates_map():
    if os.path.exists(DATES_FILE):
        try:
            with open(DATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

class OKAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/search':
            qs = parse_qs(parsed.query)
            q = qs.get('q', [''])[0]
            results = perform_search(q)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(results, ensure_ascii=False).encode('utf-8'))
            return

        if parsed.path == '/api/encyclopedia':
            data = build_encyclopedia_data()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            return

        return super().do_GET()

def perform_search(q):
    results = hybrid_search_oka(q) if q else []
    
    gemini_cats = {}
    if os.path.exists(GEMINI_CAT_FILE):
        try:
            with open(GEMINI_CAT_FILE, "r", encoding="utf-8") as f:
                gemini_cats = json.load(f)
        except Exception:
            pass
    
    privacy_map = get_youtube_privacy_map()
    dates_map = get_youtube_dates_map()
            
    for r in results:
        v_id = ""
        m = re.search(r'v=([a-zA-Z0-9_-]{11})', r.get('url', ''))
        if m:
            v_id = m.group(1)
        
        cat = gemini_cats.get(v_id)
        if not cat:
            t_lower = r.get('video_title', '').lower()
            if any(k in t_lower for k in ['週三八點半', '週三攝影週報', '週三攝影周報', '攝影週報', '攝影周報', '會後直播']):
                cat = 'live'
            elif any(k in t_lower for k in ['讀書會', '導讀', '攝影集', '畫冊', '作品集', '經典畫冊', '書報']):
                cat = 'book'
            elif '評圖' in t_lower or ('會員' in t_lower and any(k in t_lower for k in ['作業', '照片', '點評', '獨家'])):
                cat = 'member_review'
            elif any(k in t_lower for k in ['相機', '鏡頭', '實測', '評測', '開箱', '選購', '手冊', '濾鏡', '腳架', '相機包', '包款', 'sony', 'fujifilm', '富士', 'nikon', 'canon', 'ricoh', 'gr', 'gr3', 'gr3x', 'gr4', 'leica', '徠卡', '銘匠', '適馬', 'sigma', 'tamron', '騰龍', '哈蘇', 'hasselblad', 'zeiss', '蔡司', 'panasonic', 'fx30', 'fx3', 'a7', 'z8', 'z9', 'z6', 'zf', 'zfc', 'x100v', 'x100vi', 'x-t5', 'x-e4']):
                cat = 'gear'
            else:
                cat = 'daily'
        
        r['category'] = cat
        r['publish_date'] = dates_map.get(v_id, "")
        p_info = privacy_map.get(v_id)
        if p_info:
            r['is_member_only'] = p_info.get("is_member_only", False)
        else:
            r['is_member_only'] = (cat in ["member_review", "live", "book"])

    return results

def build_encyclopedia_data():
    vmap = get_video_map()
    llm_sums = get_llm_summaries()

    gemini_cats = {}
    if os.path.exists(GEMINI_CAT_FILE):
        try:
            with open(GEMINI_CAT_FILE, "r", encoding="utf-8") as f:
                gemini_cats = json.load(f)
        except Exception:
            pass

    cat_daily = []
    cat_gear = []
    cat_live = []
    cat_member_review = []
    cat_book = []

    privacy_map = get_youtube_privacy_map()
    dates_map = get_youtube_dates_map()

    for v_id, meta in list(vmap.items()):
        title = get_clean_title(v_id, meta.get("title", ""))
        url = f"https://www.youtube.com/watch?v={v_id}&t=0s"
        
        cat = gemini_cats.get(v_id)
        
        if not cat:
            t_lower = title.lower()
            if any(k in t_lower for k in ['週三八點半', '週三攝影週報', '週三攝影周報', '攝影週報', '攝影周報', '會後直播']):
                cat = 'live'
            elif any(k in t_lower for k in ['讀書會', '導讀', '攝影集', '畫冊', '作品集', '經典畫冊', '書報']):
                cat = 'book'
            elif '評圖' in t_lower or ('會員' in t_lower and any(k in t_lower for k in ['作業', '照片', '點評', '獨家'])):
                cat = 'member_review'
            elif any(k in t_lower for k in ['相機', '鏡頭', '實測', '評測', '開箱', '選購', '手冊', '濾鏡', '腳架', '相機包', '包款', 'sony', 'fujifilm', '富士', 'nikon', 'canon', 'ricoh', 'gr', 'gr3', 'gr3x', 'gr4', 'leica', '徠卡', '銘匠', '適馬', 'sigma', 'tamron', '騰龍', '哈蘇', 'hasselblad', 'zeiss', '蔡司', 'panasonic', 'fx30', 'fx3', 'a7', 'z8', 'z9', 'z6', 'zf', 'zfc', 'x100v', 'x100vi', 'x-t5', 'x-e4']):
                cat = 'gear'
            else:
                cat = 'daily'

        p_info = privacy_map.get(v_id)
        if p_info:
            is_member = p_info.get("is_member_only", False)
        else:
            is_member = (cat in ["member_review", "live", "book"])

        ai_sum = display_summary(title, llm_sums.get(url, ""), cat)

        item = {
            "id": v_id,
            "title": title,
            "url": url,
            "publish_date": dates_map.get(v_id, ""),
            "is_member_only": is_member,
            "ai_summary": ai_sum,
            "sample_quotes": [
                {
                    "timestamp": "00:00",
                    "text": title,
                    "summary": ai_sum,
                    "url": url
                }
            ]
        }

        if cat == "book":
            cat_book.append(item)
        elif cat == "live":
            cat_live.append(item)
        elif cat == "member_review":
            cat_member_review.append(item)
        elif cat == "gear":
            cat_gear.append(item)
        else:
            cat_daily.append(item)

    return {
        "channel_info": {
            "name": "我都OK啊",
            "author": "道慈老師",
            "total_videos": len(vmap)
        },
        "categories": [
            {"id": "daily", "name": "日常影片", "icon": "📸", "videos": cat_daily},
            {"id": "gear", "name": "器材評測", "icon": "📷", "videos": cat_gear},
            {"id": "live", "name": "直播存檔", "icon": "🎙️", "videos": cat_live},
            {"id": "member_review", "name": "會員評圖", "icon": "👑", "videos": cat_member_review},
            {"id": "book", "name": "讀書會", "icon": "📚", "videos": cat_book}
        ]
    }

import threading

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, OKAHandler)
    print("=" * 80, flush=True)
    print(f"🚀 OKA 全頻道 Web Server 已在 Port {port} 成功綁定啟動！", flush=True)
    print("=" * 80, flush=True)
    
    def warmup_bg():
        print("🔥 正在背景進行資料庫【RAM 記憶體熱快取預熱 (Warmup)】...", flush=True)
        try:
            from batch_rag_indexer import get_rag_chunks, get_inverted_index
            get_rag_chunks()
            get_inverted_index()
            get_video_map()
            get_title_zh_map()
            print("⚡ 記憶體預熱完成！全頻道 1,307,252 筆切片已常駐 RAM 暫存器 (總開銷 < 120MB)", flush=True)
        except Exception as e:
            print(f"⚠️ 背景預熱提醒: {e}", flush=True)

    # Production serves only static files from public/, so eagerly loading the
    # legacy 1.3M-segment Python index wastes RAM and can freeze local QA.
    # Keep it opt-in for developers still testing the compatibility API.
    if os.environ.get("ENABLE_LEGACY_API_WARMUP") == "1":
        threading.Thread(target=warmup_bg, daemon=True).start()
    else:
        print("📦 靜態模式：略過舊版 RAG API 記憶體預熱。", flush=True)
    httpd.serve_forever()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
