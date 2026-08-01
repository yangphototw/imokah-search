import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# 將專案根目錄加入 Python 搜尋路徑
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            if 'search' in path or 'q' in query_params:
                from ai_oka import hybrid_search_oka
                q = query_params.get('q', [''])[0]
                res = hybrid_search_oka(q)
            else:
                from web_server import build_encyclopedia_data
                res = build_encyclopedia_data()

            body = json.dumps(res, ensure_ascii=False).encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            err_res = {"error": f"Runtime error: {e}\n{traceback.format_exc()}"}
            self.wfile.write(json.dumps(err_res).encode('utf-8'))
