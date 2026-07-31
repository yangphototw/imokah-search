import os
import sys
import json
import time
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OKA_ROOT, "data")
INDEX_FILE = os.path.join(DATA_DIR, "oka_rag_index.json")
VECTOR_DB_DIR = os.path.join(DATA_DIR, "oka_vector_db")
VECTOR_MODEL_FILE = os.path.join(VECTOR_DB_DIR, "vector_model.pkl")
VECTOR_MATRIX_FILE = os.path.join(VECTOR_DB_DIR, "vector_matrix.npz")
CHUNKS_META_FILE = os.path.join(VECTOR_DB_DIR, "chunks_meta.pkl")

os.makedirs(VECTOR_DB_DIR, exist_ok=True)

_CACHE = {
    "vectorizer": None,
    "matrix": None,
    "chunks": None
}

def p(msg):
    print(msg, flush=True)

def build_vector_database():
    p("=" * 65)
    p("🚀 [任務二] 開始建置本地 100% 免費 Vector 語意向量庫 (1,307,252 切片)...")
    p("=" * 65)

    if not os.path.exists(INDEX_FILE):
        p(f"❌ 找不到基礎索引檔：{INDEX_FILE}")
        return

    p(f"📦 正在載入基礎 RAG 切片檔 ({os.path.getsize(INDEX_FILE)/1024/1024:.1f} MB)...")
    t0 = time.time()
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    p(f"✅ 成功載入 {len(chunks):,} 個對話切片 (耗時 {time.time()-t0:.2f} 秒)。")

    p("⚡ 正在建立微觀語意文本 (Corpus)...")
    corpus = [f"{c['video_title']} {c['text']}" for c in chunks]

    p("🧠 正在建構 C++ 極速中英文單詞/單字混合 TF-IDF 語意向量模型...")
    vectorizer = TfidfVectorizer(
        token_pattern=r'(?u)\b\w+\b|[\u4e00-\u9fa5]',
        max_features=35000,
        sublinear_tf=True
    )
    
    t1 = time.time()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    p(f"✅ 語意向量矩陣建構完成，形狀：{tfidf_matrix.shape} (耗時 {time.time()-t1:.2f} 秒)。")

    p("💾 正在持久化向量模型與索引庫至 data/oka_vector_db/...")
    
    with open(VECTOR_MODEL_FILE, "wb") as f:
        pickle.dump(vectorizer, f, protocol=pickle.HIGHEST_PROTOCOL)

    from scipy.sparse import save_npz
    save_npz(VECTOR_MATRIX_FILE, tfidf_matrix)

    lite_chunks = []
    for c in chunks:
        lite_chunks.append({
            "v_title": c["video_title"],
            "ts": c["timestamp"],
            "txt": c["text"],
            "url": c["url"]
        })

    with open(CHUNKS_META_FILE, "wb") as f:
        pickle.dump(lite_chunks, f, protocol=pickle.HIGHEST_PROTOCOL)

    p(f"🎉 本地 Vector 語意向量庫建置完成！(總費時 {time.time()-t0:.2f} 秒)")
    p(f"📁 實體檔案存放路徑：{VECTOR_DB_DIR}")

def query_vector_db(query_text, top_k=10):
    if not (os.path.exists(VECTOR_MODEL_FILE) and os.path.exists(VECTOR_MATRIX_FILE) and os.path.exists(CHUNKS_META_FILE)):
        return []

    try:
        if _CACHE["vectorizer"] is None:
            with open(VECTOR_MODEL_FILE, "rb") as f:
                _CACHE["vectorizer"] = pickle.load(f)

        if _CACHE["matrix"] is None:
            from scipy.sparse import load_npz
            _CACHE["matrix"] = load_npz(VECTOR_MATRIX_FILE)

        if _CACHE["chunks"] is None:
            with open(CHUNKS_META_FILE, "rb") as f:
                _CACHE["chunks"] = pickle.load(f)

        vectorizer = _CACHE["vectorizer"]
        tfidf_matrix = _CACHE["matrix"]
        chunks = _CACHE["chunks"]

        query_vec = vectorizer.transform([query_text])
        scores = (tfidf_matrix * query_vec.T).toarray().ravel()

        valid_indices = np.where(scores > 0)[0]
        if len(valid_indices) == 0:
            return []

        sorted_indices = valid_indices[np.argsort(scores[valid_indices])[::-1]]
        
        results = []
        seen_videos = set()
        
        for idx in sorted_indices:
            score = scores[idx]
            c = chunks[idx]
            txt = c["txt"].strip()
            
            if len(txt) < 4:
                continue
                
            v_key = (c["v_title"], c["ts"][:3])
            if v_key in seen_videos:
                continue
            seen_videos.add(v_key)

            results.append({
                "score": float(score),
                "video_title": c["v_title"],
                "timestamp": c["ts"],
                "text": txt,
                "url": c["url"]
            })
            if len(results) >= top_k:
                break
                
        return results
    except Exception as e:
        p(f"Vector search exception: {e}")
        return []

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        build_vector_database()
    elif len(sys.argv) > 1:
        test_q = sys.argv[1]
        p(f"\n🔍 測試抽象語意檢索：「{test_q}」")
        res = query_vector_db(test_q)
        for r in res:
            p(f"- [{r['score']:.4f}] [{r['video_title']} {r['timestamp']}]: {r['text']}\n  ▶️ {r['url']}")
    else:
        p("使用方式: python build_vector_db.py --build 或 python build_vector_db.py [查詢關鍵字]")
