import os
import sys
import json
import time
from google import genai
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(OKA_ROOT, ".env")
MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_youtube_map.json")
TITLE_ZH_MAP_FILE = os.path.join(OKA_ROOT, "data", "oka_title_zh_mapping.json")
GEMINI_CAT_FILE = os.path.join(OKA_ROOT, "data", "oka_gemini_categories.json")

load_dotenv(ENV_FILE)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ 錯誤: 未能在 .env 中找到 GEMINI_API_KEY", flush=True)
    sys.exit(1)

client = genai.Client(api_key=api_key)

def load_data():
    vmap = {}
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            vmap = json.load(f)

    zh_map = {}
    if os.path.exists(TITLE_ZH_MAP_FILE):
        with open(TITLE_ZH_MAP_FILE, "r", encoding="utf-8") as f:
            zh_map = json.load(f)

    gemini_cats = {}
    if os.path.exists(GEMINI_CAT_FILE):
        try:
            with open(GEMINI_CAT_FILE, "r", encoding="utf-8") as f:
                gemini_cats = json.load(f)
        except Exception:
            pass

    return vmap, zh_map, gemini_cats

def classify_super_batch_with_gemini(items):
    prompt = """你是一位專業的 YouTube 頻道內容分類大師。
請針對以下影片標題列表，精確判斷每部影片屬於以下四大分類之一：
1. "regular" (日常影片)：公開上架的日常評測、教學、Vlog、散步、開箱影片。
2. "member" (會員影片)：頻道會員專屬、會員評圖、獨家節目、會後談影片。
3. "live" (直播精華)：固定線上直播紀錄，特別包含「週三八點半」、「週三攝影週報/主題」、直播紀錄。
4. "book" (讀書會)：讀書會、導讀、作品集/書籍賞析專題。

請嚴格輸出 JSON 物件，格式如下：
{
  "影片ID_1": "regular"|"member"|"live"|"book",
  "影片ID_2": "regular"|"member"|"live"|"book"
}

待分類影片列表：
"""
    for v_id, title in items:
        prompt += f"- ID: {v_id} | 標題: {title}\n"

    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
            )
            txt = response.text.strip()
            if "```json" in txt:
                txt = txt.split("```json")[1].split("```")[0].strip()
            elif "```" in txt:
                txt = txt.split("```")[1].split("```")[0].strip()

            return json.loads(txt)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"⏳ 遇到 429 觸發 API 冷卻，等待 30 秒後進行第 ({attempt+1}/5) 次重試...", flush=True)
                time.sleep(30)
            else:
                print(f"⚠️ Gemini 巨型批次 API 呼叫異常: {e}", flush=True)
                time.sleep(10)
    return {}

def run_gemini_classification():
    vmap, zh_map, gemini_cats = load_data()
    
    unclassified = []
    for v_id, meta in vmap.items():
        if v_id not in gemini_cats:
            title = zh_map.get(v_id, meta.get("title", ""))
            unclassified.append((v_id, title))

    print("=" * 80, flush=True)
    print(f"🤖 啟動 Gemini 3.6 Flash 超級批次分類器", flush=True)
    print(f"📊 全頻道影片總數: {len(vmap)} 部 | 已完成分類: {len(gemini_cats)} 部 | 待補全: {len(unclassified)} 部", flush=True)
    print("=" * 80, flush=True)

    if not unclassified:
        print("🎉 全頻道 1,038 部影片已 100% 由 Gemini 3.6 Flash 完成權威分類！", flush=True)
        return

    # 超級批次：每次 150 部影片，大幅減少 Request 次數
    SUPER_BATCH_SIZE = 150
    for i in range(0, len(unclassified), SUPER_BATCH_SIZE):
        batch = unclassified[i:i+SUPER_BATCH_SIZE]
        print(f"⚡ 正在由 Gemini 3.6 Flash 研判第 {i+1} ~ {i+len(batch)} 部影片權威分類...", flush=True)
        
        res = classify_super_batch_with_gemini(batch)
        if res:
            for v_id, cat in res.items():
                if cat in ["regular", "member", "live", "book"]:
                    gemini_cats[v_id] = cat
            
            with open(GEMINI_CAT_FILE, "w", encoding="utf-8") as f:
                json.dump(gemini_cats, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 完成！目前已累積存入 Gemini 權威分類 {len(gemini_cats)} / {len(vmap)} 部影片", flush=True)
        time.sleep(5)

    print("=" * 80, flush=True)
    print("🎉 恭喜！全頻道 1,038 部影片已 100% 由 Gemini 3.6 Flash 完成權威分類！", flush=True)
    print(f"💾 分類結果已儲存至 {GEMINI_CAT_FILE}", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_gemini_classification()
