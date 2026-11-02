import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()
BIBLE_API_KEY = os.getenv('BIBLE_API_KEY')
headers = {'api-key': BIBLE_API_KEY}
BIBLE_API_URL=os.getenv("BIBLE_API_URL")

def bible_list():
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

