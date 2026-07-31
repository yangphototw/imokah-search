import os
import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

print("="*70, flush=True)
print("🚀 [優先佇列模式] 第一階段：全力集中顯卡算力轉譯《我都ok啊》 (共 1038 部)...", flush=True)
print("="*70, flush=True)

# 1. First transcribe all 1038 videos of OKA
oka_script = os.path.join(r"D:\Gemini_CLI\260726_AIOK", "transcribe_all_cached_oka.py")
subprocess.run([sys.executable, "-u", oka_script], cwd=r"D:\Gemini_CLI\260726_AIOK", check=True)

print("\n" + "="*70, flush=True)
print("🎉🎉《我都ok啊》全數 1038 部影片轉譯與 RAG 索引化 100% 完成！", flush=True)
print("🚀 [優先佇列模式] 第二階段：接續全力轉譯《股癌 Gooaye》 (共 682 集)...", flush=True)
print("="*70 + "\n", flush=True)

# 2. Then transcribe all 682 episodes of Gooaye
gooaye_script = os.path.join(r"D:\Gemini_CLI\260726_AIGooaye", "transcribe_all_cached_mp3.py")
subprocess.run([sys.executable, "-u", gooaye_script], cwd=r"D:\Gemini_CLI\260726_AIGooaye", check=True)

print("\n" + "="*70, flush=True)
print("🏆🏆🏆 兩大專案共 1,720 部節目/影片 100% 大滿貫轉譯與 RAG 索引化全部完美竣工！", flush=True)
print("="*70, flush=True)
