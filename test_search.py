import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('TWELVE_LABS_API_KEY')
BASE_URL = "https://api.twelvelabs.io/v1.1"

# Use your actual index_id and video_id from the output
INDEX_ID = "69e917b0736534ce03f7c143"
VIDEO_ID = "69ea229ec1f9995ff9f7f4dd"

# Test different search queries
queries = [
    "person",
    "people talking",
    "news anchor",
    "What was the senator accused of?"
]

for query in queries:
    print(f"\n{'='*50}")
    print(f"Testing: {query}")
    print('='*50)
    
    data = [
        ('index_id', INDEX_ID),
        ('query_text', query),
        ('search_options', 'visual'),
        ('page_limit', '5')
    ]
    
    response = requests.post(
        f"{BASE_URL}/search",
        headers={"x-api-key": API_KEY},
        files=data
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        results = response.json().get('data', [])
        print(f"Results found: {len(results)}")
        for r in results[:3]:
            print(f"  {r.get('start')}-{r.get('end')}s: score={r.get('score')}")
    else:
        print(f"Error: {response.text}")