"""One-off downloader for saving a Bible book as local chapter HTML files.

Set BIBLE_API_URL and BIBLE_API_KEY before running. The selected Bible ID,
book ID, chapter count, and output directory below are intentionally explicit
so the downloaded files can be reviewed before they are served by the reader.
"""

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
        f"{BIBLE_API_URL}/bibles/{bible_id}/chapters/{chapter_id}",
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
    raw_json=response.json()
    parsed_dict=raw_json.get("data",[])
    return parsed_dict




# This source and destination identify the edition and book being downloaded.
bible_id = 'de4e12af7f28f599-02' 
html_head = '<!DOCTYPE html><html lang="en"><head><meta property="og:image" content="https://angga-labola.github.io/photos/og.png"><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="color-scheme" content="dark light"><link rel="stylesheet" href="/static/styles.css"><title>Bible</title></head><body><img src="/static/photos/cross_vector.jpg" alt="Cross" height="250" width="150" class="center-block"><br><br>'
html_foot ='<script src="https://giscus.app/client.js" data-repo="Angga-Labola/Angga-Labola.github.io" data-repo-id="R_kgDOU7HrkQ" data-category="Announcements" data-category-id="DIC_kwDOU7Hrkc4DHDs-" data-mapping="pathname" data-strict="1" data-reactions-enabled="1" data-emit-metadata="1" data-input-position="top" data-theme="dark" data-lang="en" data-loading="lazy" crossorigin="anonymous" async></script></body>'
book_id='REV'
total_chapter=22


# Keep downloaded source files separate from the reader template tree; move
# reviewed chapter files under templates/bible/<BOOK>/ for the app to serve.
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
