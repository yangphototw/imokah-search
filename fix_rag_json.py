import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
RAG_INDEX = os.path.join(OKA_ROOT, "data", "oka_rag_index.json")

def fix_json():
    print("🛠️ 開始修復與還原 oka_rag_index.json...", flush=True)
    with open(RAG_INDEX, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    try:
        data = json.loads(content)
        print("✅ JSON 格式原本即正常！", flush=True)
    except Exception as e:
        print(f"⚠️ 發現修復點: {e}，進行末尾自動閉合修復...", flush=True)
        last_bracket = content.rfind("}")
        if last_bracket != -1:
            content = content[:last_bracket+1] + "\n]"
        data = json.loads(content)
        with open(RAG_INDEX, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("✅ 修復成功並覆寫！", flush=True)

if __name__ == "__main__":
    fix_json()
