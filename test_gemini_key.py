import os
import sys
from google import genai

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

api_key = "AQ.Ab8RN6IAAbWQMdmyqvyHsNsK_tjV9O52K8oYcVMjSDxUS8aEMQ"
client = genai.Client(api_key=api_key)

for m in ['gemini-3.6-flash', 'gemini-flash-latest', 'gemini-2.0-flash-lite']:
    try:
        response = client.models.generate_content(
            model=m,
            contents='請用繁體中文回答：您好！Gemini 模型連線測試。',
        )
        print(f"🎉 成功！模型 {m} 回應：", response.text.strip())
        break
    except Exception as e:
        print(f"⚠️ 模型 {m} 測試訊息：", str(e))
