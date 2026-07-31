import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# 將專案根目錄加入 Python 搜尋路徑
OKA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if OKA_ROOT not in sys.path:
    sys.path.insert(0, OKA_ROOT)

from web_server import build_encyclopedia_data
from ai_oka import hybrid_search_oka

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if path == '/api/encyclopedia' or path == '/api/encyclopedia/':
            res = build_encyclopedia_data()
        elif path == '/api/search' or path == '/api/search/':
            q = query_params.get('q', [''])[0]
            res = hybrid_search_oka(q)
        else:
            res = {"status": "ok", "message": "OKA Search API on Vercel"}
            
        self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
