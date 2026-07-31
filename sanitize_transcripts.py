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

# 攝影專有名詞與道慈老師專用錯字校正對照表
SPELL_CORRECTION_MAP = {
    "倒實老師": "道慈老師",
    "倒石老師": "道慈老師",
    "到此老師": "道慈老師",
    "倒慈老師": "道慈老師",
    "樹未相機": "數位相機",
    "樹位相機": "數位相機",
    "湯龍": "騰龍",
    "適馬": "SIGMA",
    "沃坦": "Wotancraft",
    "A7四": "A7IV",
    "A7 四": "A7IV",
    "a7四": "a7IV",
    "GR三": "GR3",
    "GR 三": "GR3",
    "gr三": "gr3",
    "偏振鏡": "偏光鏡",
    "單眼相機": "單眼相機",
    "無反相機": "無反相機",
    "尼康": "Nikon",
    "索尼": "Sony",
    "佳能": "Canon",
    "富士": "Fujifilm"
}

def clean_hallucination_repeats(text):
    """
    修正 Whisper 陷入幻覺重複的疊字/重複詞彙
    例如：將 "馬來西亞馬來西亞馬來西亞馬來西亞" 簡化為 "馬來西亞"
    """
    if not text:
        return ""
    
    # 修正 2~6 個字元的連續重複 3 次以上
    pattern = r'([\u4e00-\u9fa5a-zA-Z0-9]{2,6})\1{2,}'
    cleaned = re.sub(pattern, r'\1', text)
    
    # 修正單字連續重複 4 次以上 (例如: "的的的的" -> "的")
    single_char_pattern = r'([\u4e00-\u9fa5])\1{3,}'
    cleaned = re.sub(single_char_pattern, r'\1', cleaned)

    return cleaned

def sanitize_text(text):
    if not text:
        return ""
    
    # 1. 解除 Whisper 幻覺重複
    cleaned = clean_hallucination_repeats(text)

    # 2. 攝影專有名詞錯字校正
    for wrong, right in SPELL_CORRECTION_MAP.items():
        if wrong in cleaned:
            cleaned = cleaned.replace(wrong, right)

    return cleaned.strip()

def run_sanitization():
    print("=" * 70)
    print("🧹 開始全量修復逐字稿中的 Whisper 幻覺疊字與攝影專有名詞錯別字...")
    print("=" * 70)

    json_files = glob.glob(os.path.join(TRANSCRIPT_DIR, "*_transcript.json"))
    total_files = len(json_files)
    fixed_chunks_count = 0
    fixed_files_count = 0

    for idx, fpath in enumerate(json_files, 1):
        try:
            with open(fpath, "r", encoding="utf-8") as jf:
                chunks = json.load(jf)

            file_modified = False
            for chunk in chunks:
                orig_text = chunk.get("text", "")
                sanitized = sanitize_text(orig_text)
                if sanitized != orig_text:
                    chunk["text"] = sanitized
                    file_modified = True
                    fixed_chunks_count += 1

            if file_modified:
                with open(fpath, "w", encoding="utf-8") as jf:
                    json.dump(chunks, jf, ensure_ascii=False, indent=2)
                fixed_files_count += 1

        except Exception as e:
            pass

    print(f"✅ 修復完成！共掃描 {total_files} 部影片逐字稿。")
    print(f"  ✨ 修正了 {fixed_files_count} 部影片中的 {fixed_chunks_count:,} 個幻覺/錯字對話切片！")
    print("=" * 70)

    # 重新寫入全量 RAG 索引與向量庫
    print("🔄 正在重新同步全量 RAG 索引檔與 Vector DB...")
    os.system(f'"{sys.executable}" fix_all_titles_completely.py')
    print("🎉 全庫與網頁對話切片清洗同步完成！")

if __name__ == "__main__":
    run_sanitization()
