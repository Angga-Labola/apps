"""One-off helper to print Bible IDs available from the configured API.

This script is not part of the web app's request flow. It reads BIBLE_API_URL
and BIBLE_API_KEY from the environment (or a local .env file) and prints the
API's name-to-ID catalog.
"""

import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()
BIBLE_API_KEY = os.getenv('BIBLE_API_KEY')
headers = {'api-key': BIBLE_API_KEY}
BIBLE_API_URL=os.getenv("BIBLE_API_URL")

def bible_list():
    """Fetch the upstream Bible catalog and return its data entries."""
    response=requests.get(
        f"{BIBLE_API_URL}/bibles",
        headers=headers,
    )
    raw_json=json.loads(response.text)
    parsed_list=raw_json.get("data",[])
    return parsed_list

data = bible_list()

bible_dict={}
for bible in data:
    bible_dict[bible["name"]]=bible["id"]

for key in bible_dict.keys():
    print(f"{key}:{bible_dict[key]}")

