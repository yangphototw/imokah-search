import json
import os
import sys
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def translate_titles():
    # Read the titles to translate
    try:
        with open('data/needs_translation.json', 'r', encoding='utf-8') as f:
            needs_translation = json.load(f)
    except FileNotFoundError:
        print("Error: data/needs_translation.json not found.")
        return

    # Check for API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not set.")
        return
        
    client = genai.Client()
    translated_map = {}

    print(f"Translating {len(needs_translation)} titles...")
    
    # We can batch them to save API calls
    keys = list(needs_translation.keys())
    batch_size = 20
    
    for i in range(0, len(keys), batch_size):
        batch_keys = keys[i:i+batch_size]
        batch_data = {k: needs_translation[k] for k in batch_keys}
        
        prompt = f"""
        Translate the following YouTube video titles to Traditional Chinese (繁體中文).
        Maintain any camera model names or specific English brands (like GR IV, Sony α7R VI, Luminar Neo) in English, but translate the descriptive parts smoothly.
        Keep the prefixes like 【相機實測/主題】 intact.
        
        Input JSON:
        {json.dumps(batch_data, ensure_ascii=False)}
        
        Output valid JSON with the exact same keys and the translated string values. Do not output anything other than JSON.
        """
        
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            
            res_json = json.loads(response.text)
            for k, v in res_json.items():
                translated_map[k] = v
                
            print(f"Processed {min(i+batch_size, len(keys))}/{len(keys)}")
            
        except Exception as e:
            print(f"Error calling API: {e}")
            
    # Load existing mapping
    zh_map = {}
    try:
        with open('data/oka_title_zh_mapping.json', 'r', encoding='utf-8') as f:
            zh_map = json.load(f)
    except FileNotFoundError:
        pass
        
    # Update mapping
    for k, v in translated_map.items():
        zh_map[k] = v
        
    # Write back
    with open('data/oka_title_zh_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(zh_map, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully updated {len(translated_map)} titles in oka_title_zh_mapping.json")

if __name__ == '__main__':
    translate_titles()
