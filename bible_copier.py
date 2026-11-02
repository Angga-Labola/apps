import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()
BIBLE_API_KEY = os.getenv('BIBLE_API_KEY')
headers = {'api-key': BIBLE_API_KEY}
BIBLE_API_URL=os.getenv("BIBLE_API_URL")

def read_chapter(bible_id:str,chapter_id:str):
    response=requests.get(
        f"{BIBLE_API_URL}/{bible_id}/chapters/{chapter_id}",
        headers=headers,
        params={
            "content-type": "html",
            "include-notes": "false",
            "include-titles": "true",
            "include-chapter-numbers": "true",
            "include-verse-numbers": "true",
            "include-verse-spans": "false"
        }
    )
    raw_json=json.loads(response.text)
    parsed_dict=raw_json.get("data",[])
    return parsed_dict



bible_id = 'de4e12af7f28f599-02' 
html_head = '<!DOCTYPE html><html lang="en"><head><meta property="og:image" content="https://angga-labola.github.io/photos/og.png"><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="color-scheme" content="dark light"><link rel="stylesheet" href="/static/styles.css"><title>Bible</title></head><body><img src="/static/photos/cross_vector.jpg" alt="Cross" height="250" width="150" class="center-block"><br><br>'
html_foot ='</body>'
book_id='REV'
total_chapter=22

output_dir = f"bible/{book_id}"
os.makedirs(output_dir, exist_ok=True)


for chapter_num in range(1, total_chapter+1):
    chapter_id = f"{book_id}.{chapter_num}"
    print(f"Fetching {chapter_id}...")
    
    try:
        # Fetch the data from the API
        chapter_data = read_chapter(bible_id, chapter_id)
        html_content = chapter_data.get("content", "")
        
        if html_content:
            filename = os.path.join(output_dir, f"{book_id}_{chapter_num}.html")
            
            with open(filename, "w", encoding="utf-8") as file:
                file.write(html_head + html_content + html_foot)
                
            print(f"Saved: {filename}")
        else:
            print(f"Warning: No content found for {chapter_id}")
            
    except Exception as e:
        print(f"Failed to process {chapter_id}. Error: {e}")

print("\nFinished downloading all chapters!")
