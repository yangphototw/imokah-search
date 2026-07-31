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
CLEANED_TRANSCRIPTS_FILE = os.path.join(OKA_ROOT, "data", "oka_cleaned_transcripts.json")
API_KEY = "AQ.Ab8RN6IAAbWQMdmyqvyHsNsK_tjV9O52K8oYcVMjSDxUS8aEMQ"

client = genai.Client(api_key=API_KEY)

# 攝影專有名詞與 Whispers 錯字對照表
HOMOPHONE_MAP = {
    "我是刀子": "我是道慈",
    "我是道子": "我是道慈",
    "我是到此": "我是道慈",
    "刀子老師": "道慈老師",
    "道子老師": "道慈老師",
    "到此老師": "道慈老師",
    "到慈老師": "道慈老師",
    "導詞老師": "道慈老師",
    "倒此老師": "道慈老師",
    "刀子": "道慈",
    "道子": "道慈",
    "到慈": "道慈",
    "導詞": "道慈",
    "倒此": "道慈"
}

def clean_homophone_typos_fast(text):
    if not text: return text
    t = text
    for old_k, new_v in HOMOPHONE_MAP.items():
        t = t.replace(old_k, new_v)
    t = re.sub(r'到此(?=說|認為|表示|分享|講|覺得|實測|帶|去|在|的)', '道慈', t)
    return t

def gemini_clean_transcript_segment(text):
    """
    使用 Gemini 原廠語意能力對 Whisper 逐字稿進行深層潤飾與錯字修正
    """
    raw = clean_homophone_typos_fast(text.strip())
    if not raw: return raw

    prompt = f"""你是一位專業的繁體中文影音字幕編輯。請修正以下 YouTube 語音辨識 (Whisper) 字幕中的同音錯字（例如將「刀子/到此/道子」修正為攝影師姓名「道慈」），並修正文理不通順或口誤之處，保持原本口語說話意思，輸出極度自然通順的繁體中文對白。請直接輸出校正後的對白內容，不要附加任何解釋。

[原始對白]: {raw}
"""
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        if response and response.text:
            cleaned = clean_homophone_typos_fast(response.text.strip())
            return cleaned
    except Exception:
        pass

    return raw

def run_transcript_cleaning_pipeline(limit=1000):
    print("=" * 80, flush=True)
    print("🧠 啟動 Gemini 3.6 Flash 全頻道 Whisper 逐字稿全量語意淨化與錯字校正...", flush=True)
    print("=" * 80, flush=True)

    if not os.path.exists(RAG_INDEX_FILE):
        print(f"❌ 未找到 {RAG_INDEX_FILE}", flush=True)
        return

    with open(RAG_INDEX_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    cleaned_dict = {}
    if os.path.exists(CLEANED_TRANSCRIPTS_FILE):
        try:
            with open(CLEANED_TRANSCRIPTS_FILE, "r", encoding="utf-8") as f:
                cleaned_dict = json.load(f)
        except Exception:
            pass

    save_every = 50
    updated_count = 0

    for idx, c in enumerate(chunks[:limit]):
        url = c.get('url', '')
        txt = c.get('text', '')

        if not url or not txt: continue
        if url in cleaned_dict: continue

        # 發送 Gemini API 進行語意淨化與校正
        cleaned_txt = gemini_clean_transcript_segment(txt)
        cleaned_dict[url] = cleaned_txt
        updated_count += 1

        if updated_count % 10 == 0:
            print(f"[{updated_count}/{limit}] ✨ 已校正: 原對白「{txt[:20]}...」 ➔ 校正後「{cleaned_txt[:20]}...」", flush=True)

        if updated_count % save_every == 0:
            with open(CLEANED_TRANSCRIPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(cleaned_dict, f, ensure_ascii=False)

    with open(CLEANED_TRANSCRIPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_dict, f, ensure_ascii=False)

    print("=" * 80, flush=True)
    print(f"🎉 完成！已將全頻道 {len(cleaned_dict):,} 筆對白校正紀錄存入 {CLEANED_TRANSCRIPTS_FILE}", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    limit = 200
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    run_transcript_cleaning_pipeline(limit)
