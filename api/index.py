import json
import os
import sys
from urllib.parse import parse_qs, urlparse

# 將專案根目錄加入 Python 搜尋路徑
OKA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if OKA_ROOT not in sys.path:
    sys.path.insert(0, OKA_ROOT)

from web_server import build_encyclopedia_data
from ai_oka import hybrid_search_oka

def app(environ, start_response):
    path = environ.get('PATH_INFO', '')
    query_string = environ.get('QUERY_STRING', '')
    query_params = parse_qs(query_string)
    
    if '/api/encyclopedia' in path:
        res = build_encyclopedia_data()
    elif '/api/search' in path:
        q = query_params.get('q', [''])[0]
        res = hybrid_search_oka(q)
    else:
        res = {"status": "ok", "message": "OKA Search API on Vercel"}

    body = json.dumps(res, ensure_ascii=False).encode('utf-8')
    status = '200 OK'
    headers = [
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Access-Control-Allow-Origin', '*'),
        ('Content-Length', str(len(body)))
    ]
    start_response(status, headers)
    return [body]
