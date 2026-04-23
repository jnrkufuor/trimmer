import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

API_KEY = os.getenv('TWELVE_LABS_API_KEY')
BASE_URL = "https://api.twelvelabs.io/v1.1"
INDEX_ID = "69e917b0736534ce03f7c143"  # Your index ID from the output

print("="*70)
print("TWELVE LABS API DEBUG SCRIPT")
print("="*70)

print(f"\nConfiguration:")
print(f"  API Key: {API_KEY[:20]}...")
print(f"  Base URL: {BASE_URL}")
print(f"  Index ID: {INDEX_ID}")

# Test 1: Check if API key works
print("\n" + "="*70)
print("TEST 1: Verify API Key")
print("="*70)
response = requests.get(f"{BASE_URL}/indexes", headers={"x-api-key": API_KEY})
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("✓ API Key is valid!")
    indexes = response.json().get('data', [])
    print(f"  You have {len(indexes)} index(es)")
else:
    print("✗ API Key issue!")
    print(f"  Response: {response.text}")

# Test 2: Check specific index
print("\n" + "="*70)
print("TEST 2: Check Index Details")
print("="*70)
response = requests.get(f"{BASE_URL}/indexes/{INDEX_ID}", headers={"x-api-key": API_KEY})
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    index_data = response.json()
    print("✓ Index found!")
    print(f"  Name: {index_data.get('index_name')}")
    print(f"  Models: {json.dumps(index_data.get('models'), indent=4)}")
    print(f"  Created: {index_data.get('created_at')}")
else:
    print("✗ Index not found!")
    print(f"  Response: {response.text}")

# Test 3: List videos in index
print("\n" + "="*70)
print("TEST 3: List Videos in Index")
print("="*70)
response = requests.get(f"{BASE_URL}/indexes/{INDEX_ID}/videos", headers={"x-api-key": API_KEY})
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    videos_data = response.json()
    videos = videos_data.get('data', [])
    print(f"✓ Found {len(videos)} video(s) in index")
    
    for i, video in enumerate(videos):
        print(f"\n  Video {i+1}:")
        print(f"    ID: {video.get('_id')}")
        print(f"    Status: {video.get('indexed_at')}")
        metadata = video.get('metadata', {})
        print(f"    Duration: {metadata.get('duration')}s")
        print(f"    Filename: {metadata.get('filename')}")
        print(f"    Created: {video.get('created_at')}")
else:
    print("✗ Could not list videos!")
    print(f"  Response: {response.text}")

# Test 4: Try different search formats
print("\n" + "="*70)
print("TEST 4: Testing Different Search Formats")
print("="*70)

test_query = "person"

# Format A: Multipart with 'query'
print("\n--- Format A: Multipart with 'query' ---")
files_a = {
    'index_id': (None, INDEX_ID),
    'query': (None, test_query),
    'search_options': (None, 'visual'),
    'page_limit': (None, '5')
}
response = requests.post(f"{BASE_URL}/search", headers={"x-api-key": API_KEY}, files=files_a)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:400]}")

# Format B: Multipart with 'query_text'
print("\n--- Format B: Multipart with 'query_text' ---")
files_b = {
    'index_id': (None, INDEX_ID),
    'query_text': (None, test_query),
    'search_options': (None, 'visual'),
    'page_limit': (None, '5')
}
response = requests.post(f"{BASE_URL}/search", headers={"x-api-key": API_KEY}, files=files_b)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:400]}")

# Format C: Multipart with multiple search_options
print("\n--- Format C: Multipart with list of tuples ---")
data_c = [
    ('index_id', INDEX_ID),
    ('query_text', test_query),
    ('search_options', 'visual'),
    ('search_options', 'conversation'),
    ('page_limit', '5')
]
response = requests.post(f"{BASE_URL}/search", headers={"x-api-key": API_KEY}, files=data_c)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:400]}")

# Format D: JSON format
print("\n--- Format D: JSON payload ---")
headers_json = {"x-api-key": API_KEY, "Content-Type": "application/json"}
payload_d = {
    "index_id": INDEX_ID,
    "query": test_query,
    "search_options": ["visual"],
    "page_limit": 5
}
response = requests.post(f"{BASE_URL}/search", headers=headers_json, json=payload_d)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:400]}")

# Format E: Try 'options' instead of 'search_options'
print("\n--- Format E: Using 'options' field ---")
files_e = {
    'index_id': (None, INDEX_ID),
    'query_text': (None, test_query),
    'options': (None, 'visual'),
    'page_limit': (None, '5')
}
response = requests.post(f"{BASE_URL}/search", headers={"x-api-key": API_KEY}, files=files_e)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:400]}")

# Test 5: Try with different API versions
print("\n" + "="*70)
print("TEST 5: Testing Different API Versions")
print("="*70)

versions = ["v1", "v1.1", "v1.2", "v1.3"]

for version in versions:
    print(f"\n--- Testing {version} ---")
    test_url = f"https://api.twelvelabs.io/{version}/search"
    
    files = {
        'index_id': (None, INDEX_ID),
        'query_text': (None, test_query),
        'page_limit': (None, '5')
    }
    
    response = requests.post(test_url, headers={"x-api-key": API_KEY}, files=files)
    print(f"URL: {test_url}")
    print(f"Status: {response.status_code}")
    if response.status_code != 404:
        print(f"Response: {response.text[:300]}")

# Test 6: Check for gist/summary endpoint
print("\n" + "="*70)
print("TEST 6: Testing Gist/Summary Endpoint")
print("="*70)

response = requests.get(f"{BASE_URL}/gist", headers={"x-api-key": API_KEY})
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:300]}")

print("\n" + "="*70)
print("DEBUG SCRIPT COMPLETE")
print("="*70)
print("\nPlease copy ALL the output above and share it!")