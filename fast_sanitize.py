import os
import sys
import json
import glob
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")

SPELL_MAP = {
    "倒實老師": "道慈老師", "倒石老師": "道慈老師", "到此老師": "道慈老師", "倒慈老師": "道慈老師",
    "樹未相機": "數位相機", "樹位相機": "數位相機", "湯龍": "騰龍", "適馬": "SIGMA",
    "沃坦": "Wotancraft", "A7四": "A7IV", "A7 四": "A7IV", "a7四": "a7IV", "GR三": "GR3", "GR 三": "GR3"
}

def clean_text(text):
    if not text:
        return ""
    # 解除 Whisper 幻覺重複 (例如: 馬來西亞馬來西亞馬來西亞...)
    c = re.sub(r'([\u4e00-\u9fa5a-zA-Z0-9]{2,6})\1{2,}', r'\1', text)
    c = re.sub(r'([\u4e00-\u9fa5])\1{3,}', r'\1', c)
    for k, v in SPELL_MAP.items():
        if k in c:
            c = c.replace(k, v)
    return c.strip()

def run():
    print("=" * 60, flush=True)
    print("🧹 開始高倍速清洗 1,038 部影片逐字稿中之幻覺疊字與同音錯字...", flush=True)
    print("=" * 60, flush=True)

    files = glob.glob(os.path.join(TRANSCRIPT_DIR, "*_transcript.json"))
    fixed_chunks = 0
    fixed_files = 0

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as jf:
                chunks = json.load(jf)
            file_changed = False
            for chunk in chunks:
                orig = chunk.get("text", "")
                san = clean_text(orig)
                if san != orig:
                    chunk["text"] = san
                    file_changed = True
                    fixed_chunks += 1
            if file_changed:
                with open(fpath, "w", encoding="utf-8") as jf:
                    json.dump(chunks, jf, ensure_ascii=False, indent=2)
                fixed_files += 1
        except Exception:
            pass

    print(f"✅ 清洗完成！修復 {fixed_files} 部影片中的 {fixed_chunks:,} 個對話片段！", flush=True)
    
    # 重新寫入全量 RAG 索引
    print("🔄 正在更新全量 RAG 索引...", flush=True)
    os.system(f'"{sys.executable}" build_knowledge_base.py')
    print("🎉 逐字稿清洗與索引同步完畢！", flush=True)

if __name__ == "__main__":
    run()
