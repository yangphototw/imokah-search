import gzip
import os
import shutil
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")

large_files = [
    "oka_rag_index.json",
    "oka_llm_summaries.json",
    "oka_inverted_index.json",
    "oka_ai_summaries.json",
    "oka_knowledge_encyclopedia.json"
]

print("🚀 開始以 Gzip 壓縮大於 50MB 的資料庫檔案以通過 GitHub 100MB 限制...")

for fname in large_files:
    fpath = os.path.join(DATA_DIR, fname)
    if os.path.exists(fpath):
        gz_path = fpath + ".gz"
        print(f"正在壓縮 {fname} -> {fname}.gz ...")
        with open(fpath, 'rb') as f_in:
            with gzip.open(gz_path, 'wb', compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        orig_mb = os.path.getsize(fpath) / (1024 * 1024)
        gz_mb = os.path.getsize(gz_path) / (1024 * 1024)
        print(f"   ✅ 原始大小: {orig_mb:.2f} MB ➔ 壓縮後: {gz_mb:.2f} MB (< 100MB 限制!)")

# 也壓縮 vector db chunks_meta.pkl
pkl_path = os.path.join(DATA_DIR, "oka_vector_db", "chunks_meta.pkl")
if os.path.exists(pkl_path):
    gz_pkl = pkl_path + ".gz"
    print("正在壓縮 chunks_meta.pkl -> chunks_meta.pkl.gz ...")
    with open(pkl_path, 'rb') as f_in:
        with gzip.open(gz_pkl, 'wb', compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
    orig_mb = os.path.getsize(pkl_path) / (1024 * 1024)
    gz_mb = os.path.getsize(gz_pkl) / (1024 * 1024)
    print(f"   ✅ 原始大小: {orig_mb:.2f} MB ➔ 壓縮後: {gz_mb:.2f} MB (< 100MB 限制!)")

print("=" * 80)
print("🎉 所有大檔均已壓縮完成！Ready for GitHub Push!")
print("=" * 80)
