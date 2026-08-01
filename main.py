import sys
import os
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_oka import hybrid_search_oka

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
ENCYCLOPEDIA_FILE = os.path.join(OKA_ROOT, "data", "oka_knowledge_encyclopedia.json")
TREE_FILE = os.path.join(OKA_ROOT, "data", "oka_knowledge_tree.md")

def show_banner():
    print("\n" + "="*70)
    print(" 🎬 歡迎使用【《我都ok啊》攝影與生活 AI 專家系統】 (AIOK Expert)")
    print(" 📌 頻道：@imokahhhh | 收錄全頻道 1,038 部影片 | 1,307,252 個秒級對話切片")
    print(" ⚡ 核心能力：5大主題知識樹 + 本地 100% 免費 Vector 語意向量庫")
    print("="*70)

def show_knowledge_summary():
    if not os.path.exists(ENCYCLOPEDIA_FILE):
        print("⚠️ 知識庫大百科尚未建置。")
        return
    with open(ENCYCLOPEDIA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("metadata", {})
    categories = data.get("categories", [])

    print(f"\n📊 【《我都ok啊》全頻道主題百科統計】 (總計 {meta.get('total_videos', 0)} 部影片)")
    print("-" * 50)
    for cat in categories:
        print(f"  {cat['icon']} {cat['name']} (`{len(cat['videos'])}` 部影片)")
        print(f"     └ 簡介: {cat['desc']}")
    print("-" * 50)
    print(f"📄 詳細 Markdown 知識樹請參閱：{TREE_FILE}\n")

def search_and_display(query, top_k=10):
    """Run the maintained lexical search engine and format a compact CLI view."""
    results = hybrid_search_oka(query, top_k=top_k)
    if not results:
        print(f"\n找不到與「{query}」相關的影片或對白。")
        return

    print(f"\n🔎 「{query}」前 {min(len(results), top_k)} 筆結果：")
    for index, result in enumerate(results[:top_k], start=1):
        print(f"\n[{index}] {result['video_title']}  {result['timestamp']}")
        print(f"    {result.get('topic_tag', '💡 【核心觀點】')}")
        print(f"    {result.get('summary', result.get('text', ''))}")
        print(f"    {result['url']}")

def main():
    show_banner()
    show_knowledge_summary()
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        search_and_display(query)
        return

    print("💡 提示：您可以輸入任何抽象問題或器材關鍵字（例如：「對街拍尷尬的看法」、「Nikon Zf 評測」、「日本自駕建議」）")
    print("   輸入 'tree' 查看知識樹概覽，輸入 'exit' 或 'q' 離開。")

    while True:
        try:
            user_input = input("\n🎙️ 請輸入您的問題或關鍵字: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q", "離開"]:
                print("\n感謝使用《我都ok啊》AI 專家系統！我們下次見！👋")
                break
            if user_input.lower() in ["tree", "百科", "目錄", "5大主題"]:
                show_knowledge_summary()
                continue

            search_and_display(user_input)

        except (KeyboardInterrupt, EOFError):
            print("\n再會！👋")
            break

if __name__ == "__main__":
    main()
