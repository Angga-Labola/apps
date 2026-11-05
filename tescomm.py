import requests

response= requests.get("https://bible.helloao.org/api/available_commentaries.json")

raw_json=response.json()
list=raw_json.get("commentaries")
for item in list:
    print(item["id"])

    