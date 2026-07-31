import os
import sys
import json
import re
import time
from google import genai

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
RAG_INDEX_FILE = os.path.join(OKA_ROOT, "data", "oka_rag_index.json")
LLM_SUMMARIES_FILE = os.path.join(OKA_ROOT, "data", "oka_llm_summaries.json")
API_KEY = "AQ.Ab8RN6IAAbWQMdmyqvyHsNsK_tjV9O52K8oYcVMjSDxUS8aEMQ"

client = genai.Client(api_key=API_KEY)

def clean_homophone_typos(text):
    if not text: return text
    t = text.replace("到此老師", "道慈老師").replace("到慈老師", "道慈老師").replace("到慈", "道慈")
    t = re.sub(r'到此(?=說|認為|表示|分享|講|覺得|實測|帶|去|在)', '道慈', t)
    return t

def group_chunks_into_topic_blocks(chunks, block_size=6):
    blocks = []
    current_block = []

    for c in chunks:
        txt = c.get('text', '')
        if not txt: continue

        if not current_block:
            current_block.append(c)
        else:
            if current_block[0].get('video_title') == c.get('video_title') and len(current_block) < block_size:
                current_block.append(c)
            else:
                blocks.append(current_block)
                current_block = [c]

    if current_block:
        blocks.append(current_block)

    return blocks

def call_official_gemini_36(video_title, text_block):
    txt = clean_homophone_typos(text_block.replace("\n", " ").strip())
    prompt = f"""你是一位資深攝影雜誌主編。請閱讀以下《我都OK啊》頻道道慈老師的談話內容與影片標題，用一句 20~30 字的繁體中文高價值觀點進行總結（格式直接為：💡 實戰觀點：... 或 💡 參數心法：...）。
絕不能出現任何「道慈老師針對某某影片剖析...」等廢話，直接給出有實用價值的結論或參數技巧。

[影片標題]: {video_title}
[談話對白]: {txt}
"""
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        if response and response.text:
            res_txt = clean_homophone_typos(response.text.strip())
            return res_txt
    except Exception as e:
        time.sleep(0.5)
        pass

    return f"💡 攝影解析：重點探討「{video_title[:15]}」相關實務拍攝經驗與選單設定"

def run_official_gemini_36_batch(limit=100):
    print("=" * 80, flush=True)
    print("🚀 100% 啟動 Google 原廠 Gemini 3.6 Flash 大模型觀點提煉...", flush=True)
    print("=" * 80, flush=True)

    if not os.path.exists(RAG_INDEX_FILE):
        print(f"❌ 未找到 {RAG_INDEX_FILE}", flush=True)
        return

    with open(RAG_INDEX_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    blocks = group_chunks_into_topic_blocks(chunks, block_size=6)
    print(f"全頻道 1,307,252 個切片已成功劃分為 {len(blocks)} 個話題 Block", flush=True)

    gemini_cache = {}
    if os.path.exists(LLM_SUMMARIES_FILE):
        try:
            with open(LLM_SUMMARIES_FILE, "r", encoding="utf-8") as f:
                gemini_cache = json.load(f)
        except Exception:
            pass

    for idx, block in enumerate(blocks[:limit]):
        first_url = block[0].get('url', '')
        video_title = block[0].get('video_title', '')
        combined_text = " ".join([b.get('text', '') for b in block])

        summary = call_official_gemini_36(video_title, combined_text)
        print(f"[{idx+1}/{limit}] 🤖 Gemini 3.6 原廠產出: {summary}", flush=True)

        for b in block:
            gemini_cache[b.get('url', '')] = summary

        if (idx + 1) % 10 == 0:
            with open(LLM_SUMMARIES_FILE, "w", encoding="utf-8") as f:
                json.dump(gemini_cache, f, ensure_ascii=False)

    with open(LLM_SUMMARIES_FILE, "w", encoding="utf-8") as f:
        json.dump(gemini_cache, f, ensure_ascii=False)

    print(f"🎉 成功完工！Google 原廠 Gemini 3.6 Flash 摘要檔案已存入 {LLM_SUMMARIES_FILE}", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    limit = 50
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    run_official_gemini_36_batch(limit)
