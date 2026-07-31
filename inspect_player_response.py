import urllib.request
import re
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

vids = ['l9_Cg05mOlQ', 'U7V0aIPH2kE', '6QQjepAQz6Q']

for vid in vids:
    url = f'https://www.youtube.com/watch?v={vid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            # Find ytInitialPlayerResponse
            m = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});</script>', html)
            if not m:
                m = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});var', html)
            
            if m:
                data = json.loads(m.group(1))
                playability = data.get('playabilityStatus', {})
                status = playability.get('status')
                reason = playability.get('reason')
                
                microformat = data.get('microformat', {}).get('playerMicroformatRenderer', {})
                is_unlisted = microformat.get('isUnlisted', False)
                is_family_safe = microformat.get('isFamilySafe', False)
                
                print(f"VID: {vid}")
                print(f"  status: {status}")
                print(f"  reason: {reason}")
                print(f"  isUnlisted: {is_unlisted}")
            else:
                print(f"VID: {vid} - ytInitialPlayerResponse not found")
    except Exception as e:
        print(f"VID: {vid} Error: {e}")
