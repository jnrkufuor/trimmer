import requests
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv('TWELVE_LABS_API_KEY')

print(f"Testing API Key: {API_KEY[:10]}...")

# Try different API versions
versions = ["v1.3" ,"v1.2", "v1.1", "v1"]

for version in versions:
    url = f"https://api.twelvelabs.io/{version}/indexes"
    headers = {"x-api-key": API_KEY}
    
    print(f"\nTrying {version}...")
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
    
    if response.status_code == 200:
        print(f"✓ SUCCESS! Use: {version}")
        break