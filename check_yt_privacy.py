import urllib.request
import re
import json
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Test a few videos: regular, live, member, book
vids = ['l9_Cg05mOlQ', 'U7V0aIPH2kE', '6QQjepAQz6Q', '0-0LG4yED1E']

for vid in vids:
    url = f'https://www.youtube.com/watch?v={vid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Accept-Language': 'zh-TW,zh;q=0.9'})
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            is_unlisted = '"isUnlisted":true' in html or '"unlisted":true' in html
            is_members_only = 'UNPLAYABLE' in html or '會員專屬' in html or 'isMembersOnly":true' in html or 'PLAYABILITY_STATUS_MEMBERS_ONLY' in html or '加入這部影片所屬的頻道' in html
            
            # Find title
            title_m = re.search(r'<title>(.*?)</title>', html)
            title = title_m.group(1) if title_m else ""
            
            print(f"VID: {vid} | Unlisted: {is_unlisted} | MembersOnly: {is_members_only} | Title: {title}")
            
    except Exception as e:
        print(f"VID: {vid} Error: {e}")
