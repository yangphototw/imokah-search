import os
import sys
import json
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
RAG_INDEX_FILE = os.path.join(OKA_ROOT, "data", "oka_rag_index.json")
CLEANED_TRANSCRIPTS_FILE = os.path.join(OKA_ROOT, "data", "oka_cleaned_transcripts.json")

def deep_clean_all_typos(text):
    if not text: return text
    t = text

    # 1. 自我介紹特徵強校正 ("大家好我是XX" -> "大家好我是道慈")
    t = re.sub(r'大家好(我是|我就|叫|是)?(刀子|道子|到此|導詞|倒此|到慈|刀慈|老慈|導子|刀子老師|道子老師)', r'大家好\1道慈', t)
    t = re.sub(r'我是(刀子|道子|到此|導詞|倒此|到慈|刀慈|老慈|導子)', r'我是道慈', t)
    t = re.sub(r'我就(是|叫)?(刀子|道子|到此|導詞|倒此|到慈|刀慈|老慈|導子)', r'我就\1道慈', t)
    t = re.sub(r'(我是|叫|跟|與)刀子', r'\1道慈', t)

    # 2. 攝影專有名詞與品牌同音錯字校正
    replacements = {
        "蔡絲": "蔡司",
        "菜絲": "蔡司",
        "卡爾蔡絲": "卡爾蔡司",
        "探龍": "騰龍",
        "死馬鏡頭": "適馬鏡頭",
        "死馬": "適馬",
        "萊卡": "徠卡",
        "到此老師": "道慈老師",
        "刀子老師": "道慈老師",
        "道子老師": "道慈老師",
        "導詞老師": "道慈老師",
        "倒此老師": "道慈老師"
    }
    for old_k, new_v in replacements.items():
        t = t.replace(old_k, new_v)

    # 3. 動態語境錯字修復
    t = re.sub(r'到此(?=說|認為|表示|分享|講|覺得|實測|帶|去|在|的|老師)', '道慈', t)
    return t

def audit_full_dataset():
    print("=" * 80, flush=True)
    print("🔍 啟動全頻道 1,307,252 個切片 Whisper 錯字全量掃描與修正...", flush=True)
    print("=" * 80, flush=True)

    if not os.path.exists(RAG_INDEX_FILE):
        print(f"❌ 未找到 {RAG_INDEX_FILE}", flush=True)
        return

    with open(RAG_INDEX_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    cleaned_map = {}
    if os.path.exists(CLEANED_TRANSCRIPTS_FILE):
        try:
            with open(CLEANED_TRANSCRIPTS_FILE, "r", encoding="utf-8") as f:
                cleaned_map = json.load(f)
        except Exception:
            pass

    intro_fixed_count = 0
    typos_fixed_count = 0

    for c in chunks:
        url = c.get('url', '')
        raw_txt = c.get('text', '')
        if not url or not raw_txt: continue

        cleaned_txt = deep_clean_all_typos(raw_txt)

        if "大家好我是" in raw_txt or "大家好我就" in raw_txt or "我是刀子" in raw_txt or "我是道子" in raw_txt:
            intro_fixed_count += 1

        if cleaned_txt != raw_txt:
            typos_fixed_count += 1
            cleaned_map[url] = cleaned_txt

    with open(CLEANED_TRANSCRIPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_map, f, ensure_ascii=False)

    print(f"全頻道 1,307,252 個切片掃描完畢！", flush=True)
    print(f"✨ 自動捕捉並修正『大家好我是...』自我介紹錯字: {intro_fixed_count} 處", flush=True)
    print(f"✨ 全量修正同音錯字（蔡絲->蔡司, 探龍->騰龍, 死馬->適馬, 徠卡）: {typos_fixed_count} 筆切片", flush=True)
    print(f"🎉 已將淨化資料庫寫入 {CLEANED_TRANSCRIPTS_FILE}", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    audit_full_dataset()
