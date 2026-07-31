import os
import sys
import json
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

def run_real_gemini_36_conversion(limit=60):
    print("=" * 80, flush=True)
    print("🤖 啟動 100% Google 原廠 Gemini 3.6 Flash 模型逐段深度讀取...", flush=True)
    print("=" * 80, flush=True)

    with open(RAG_INDEX_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # 聚類
    blocks = []
    curr = []
    for c in chunks:
        if not curr: curr.append(c)
        elif curr[0].get('video_title') == c.get('video_title') and len(curr) < 5:
            curr.append(c)
        else:
            blocks.append(curr)
            curr = [c]
    if curr: blocks.append(curr)

    gemini_cache = {}
    if os.path.exists(LLM_SUMMARIES_FILE):
        try:
            with open(LLM_SUMMARIES_FILE, "r", encoding="utf-8") as f:
                gemini_cache = json.load(f)
        except Exception:
            pass

    for idx, block in enumerate(blocks[:limit]):
        title = block[0].get('video_title', '')
        txt = " ".join([b.get('text', '') for b in block])

        prompt = f"""你是一位資深攝影雜誌主編。請閱讀以下《我都OK啊》頻道道慈老師的談話對白，用一句 20~30 字的繁體中文極致觀點進行總結（格式為：💡 實戰觀點：... 或 💡 參數心法：...）。
絕對不許出現「道慈老師剖析/分享」等水文套語，必須是純乾貨結論。
[標題]: {title}
[對白]: {txt}"""

        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
            )
            if response and response.text:
                summary = clean_homophone_typos(response.text.strip())
                print(f"[{idx+1}/{limit}] 🤖 Gemini 3.6 API 實時對白觀點: {summary}", flush=True)
                for b in block:
                    gemini_cache[b.get('url', '')] = summary
        except Exception as e:
            print(f"⚠️ [{idx+1}] API 訊息: {str(e)}", flush=True)

        if (idx + 1) % 10 == 0:
            with open(LLM_SUMMARIES_FILE, "w", encoding="utf-8") as f:
                json.dump(gemini_cache, f, ensure_ascii=False)

    with open(LLM_SUMMARIES_FILE, "w", encoding="utf-8") as f:
        json.dump(gemini_cache, f, ensure_ascii=False)

    print("=" * 80, flush=True)
    print("🎉 完成！真正的 Gemini 3.6 API 逐段摘要已儲存完畢！", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_real_gemini_36_conversion()
