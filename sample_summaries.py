import os
import sys
import json
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
LLM_SUMMARIES_FILE = os.path.join(OKA_ROOT, "data", "oka_llm_summaries.json")
RAG_INDEX_FILE = os.path.join(OKA_ROOT, "data", "oka_rag_index.json")

def sample():
    for _ in range(5):
        try:
            with open(LLM_SUMMARIES_FILE, "r", encoding="utf-8") as f:
                sums = json.load(f)
                keys = list(sums.keys())
                print(f"目前已儲存 摘要筆數: {len(sums):,} 筆\n", flush=True)
                
                # 選選不同題材切片
                sample_indices = [1500, 5000, 12000, 18000, 25000]
                for idx in sample_indices:
                    if idx < len(keys):
                        k = keys[idx]
                        print(f"▶️ URL: {k}")
                        print(f"💡 AI 觀點 Summary: {sums[k]}")
                        print("-" * 60, flush=True)
                return
        except Exception:
            time.sleep(0.5)

if __name__ == "__main__":
    sample()
