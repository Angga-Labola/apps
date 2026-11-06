import requests
from dotenv import load_dotenv
load_dotenv()
import os
SOKOBAN_KEY=os.getenv("SOKOBAN_KEY")

params={"key" : SOKOBAN_KEY}
response= requests.post("https://letslogic.com/api/v1/collection/550", params=params)
parsed_list= response.json()
