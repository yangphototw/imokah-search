import urllib.request
import re
import json
import time
import sys

# Windows cp950 fix
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def fetch_titles():
    try:
        with open('data/needs_translation.json', 'r', encoding='utf-8') as f:
            needs_translation = json.load(f)
    except Exception as e:
        print(f"Error loading needs_translation.json: {e}")
        return

    zh_map = {}
    try:
        with open('data/oka_title_zh_mapping.json', 'r', encoding='utf-8') as f:
            zh_map = json.load(f)
    except FileNotFoundError:
        pass

    count = 0
    total = len(needs_translation)
    print(f"Fetching {total} original titles from YouTube...")

    for vid in needs_translation:
        url = f'https://www.youtube.com/watch?v={vid}'
        req = urllib.request.Request(url, headers={'Accept-Language': 'zh-TW,zh;q=0.9'})
        
        try:
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                m = re.search(r'<title>(.*?)</title>', html)
                if m:
                    title = m.group(1).replace(' - YouTube', '').replace('&#39;', "'").replace('&amp;', '&')
                    zh_map[vid] = title
                    count += 1
                    print(f"[{count}/{total}] {vid} -> {title}")
        except Exception as e:
            print(f"Failed {vid}: {e}")
            
        time.sleep(0.5)

    with open('data/oka_title_zh_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(zh_map, f, ensure_ascii=False, indent=2)
        
    print(f"Updated {count} titles in oka_title_zh_mapping.json")

if __name__ == '__main__':
    fetch_titles()
