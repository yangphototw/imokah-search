import os
import sys
import json
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
LLM_SUMMARIES_FILE = os.path.join(OKA_ROOT, "data", "oka_llm_summaries.json")
RAG_INDEX_FILE = os.path.join(OKA_ROOT, "data", "oka_rag_index.json")

def print_samples():
    sums = None
    for _ in range(5):
        try:
            with open(LLM_SUMMARIES_FILE, "r", encoding="utf-8") as f:
                sums = json.load(f)
                break
        except Exception:
            time.sleep(0.5)

    if not sums:
        print("背景檔案寫入中，請再試一次", flush=True)
        return

    with open(RAG_INDEX_FILE, "r", encoding="utf-8") as f:
        rag = json.load(f)

    rag_map = {c.get('url', ''): c for c in rag if 'url' in c}
    keys = list(sums.keys())
    
    indices = [100, 5000, 15000, 30000]
    print("=" * 80)
    print("🧠 【全頻道實例對照】AI 觀點 Summary 提煉能力範例：")
    print("=" * 80 + "\n")

    for idx in indices:
        if idx < len(keys):
            k = keys[idx]
            chunk = rag_map.get(k, {})
            v_title = chunk.get('video_title', '未知標題')
            orig_text = chunk.get('text', '')
            summary = sums[k]

            print(f"🎬 [影片標題]: {v_title}")
            print(f"💬 [頻道原對白]: 「{orig_text}」")
            print(f"💡 [AI 觀點 Summary]: {summary}")
            print(f"▶️ [YouTube 時間點播]: {k}")
            print("-" * 80 + "\n")

if __name__ == "__main__":
    print_samples()
