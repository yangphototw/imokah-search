FROM python:3.11-slim

WORKDIR /app

# 安裝基本依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製全站代碼與知識庫資料
COPY . .

EXPOSE 8080

CMD ["python", "web_server.py"]
