import os
import sys
import json
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = "C:/Users/xab39/.gemini/antigravity-cli/brain/a3f6ef71-0437-4d82-82f2-466a76b3b56b/.system_generated/tasks/task-1639.log"
TOTAL_BLOCKS = 218309

def check_percentage():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    m = re.search(r'已成功提煉並儲存 (\d+) / (\d+)', line)
                    if m:
                        curr = int(m.group(1))
                        tot = int(m.group(2))
                        pct = (curr / tot) * 100
                        print(f"📊 【全頻道 AI 摘要即時進度】: {curr:,} / {tot:,} 個話題 Block ({pct:.2f}%)", flush=True)
                        return curr, tot, pct
        except Exception:
            pass

    print("📊 【全頻道 AI 摘要即時進度】: 啟動計算中...", flush=True)
    return 0, TOTAL_BLOCKS, 0.0

if __name__ == "__main__":
    check_percentage()
