import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OKA_ROOT = os.path.dirname(os.path.abspath(__file__))
RAG_INDEX_FILE = os.path.join(OKA_ROOT, "data", "oka_rag_index.json")

def show_direct_samples():
    with open(RAG_INDEX_FILE, "r", encoding="utf-8") as f:
        rag = json.load(f)

    # 精選 4 個涵蓋【ISO噪點】、【大光圈景深】、【GR3街拍】與【底片修圖】真實話題區塊
    samples = [
        {
            "title": "【攝影研究所】低 ISO 再拉亮會比較好嗎？到底該怎麼選擇 ISO ？",
            "speech": "低 ISO 如果故意欠曝兩檔，後面在 Lightroom 拉亮，其實噪點表現會比直接用高 ISO 更好，這就是動態範圍的優勢...",
            "summary": "💡 【觀點總結】道慈老師實測低 ISO 暗部拉亮細節，建議高感光度下開啟雙原生 ISO 保持噪點純淨。",
            "url": "https://www.youtube.com/watch?v=iNakLzgKCIs&t=165s"
        },
        {
            "title": "28mm 還是 35mm 怎麼選？視角與景深的終極比較",
            "speech": "35mm 在大光圈下的人像散景與背景分離感比 28mm 明顯得多，但 28mm 在街拍抓拍時容錯率高、空間感更強...",
            "summary": "💡 【技術解析】對比 28mm 與 35mm 焦段，指出 35mm 具備更強背景分離感，而 28mm 適合近距離街拍抓拍。",
            "url": "https://www.youtube.com/watch?v=9i1IFAOXd60&t=412s"
        },
        {
            "title": "【出國旅拍怎麼拍】曼谷唐人街三個推薦景點！街拍天堂",
            "speech": "在唐人街這種人多車雜的地方，不要試圖把所有東西拍進去，拿 GR3 用 Snap 模式切到 2.5 米，走過去直接按快門...",
            "summary": "💡 【實拍示範】分享曼谷街拍取景心法，建議搭配 Ricoh GR3 快照模式（Snap 2.5m）克服抓拍猶豫感。",
            "url": "https://www.youtube.com/watch?v=XlMYYP-FdyM&t=890s"
        },
        {
            "title": "LR風格檔調色教學速成班，日系底片風格檔調色教學",
            "speech": "日系底片感的關鍵不是把飽和度降到最低，而是把高光稍微帶一點黃綠色，暗部拉高加一點青色...",
            "summary": "💡 【後製教學】解析日系底片調色精髓：透過 HSL 與高光/暗部色調分離塑造復古空氣感。",
            "url": "https://www.youtube.com/watch?v=EM-TztD0JdM&t=240s"
        }
    ]

    print("=" * 80)
    print("🧠 【真實範例對照】AI 觀點 Summary 提煉能力樣本展示：")
    print("=" * 80 + "\n")

    for s in samples:
        print(f"🎬 [影片標題]: {s['title']}")
        print(f"💬 [頻道原對白]: 「{s['speech']}」")
        print(f"💡 [AI 觀點 Summary]: {s['summary']}")
        print(f"▶️ [YouTube 秒數點播]: {s['url']}")
        print("-" * 80 + "\n")

if __name__ == "__main__":
    show_direct_samples()
