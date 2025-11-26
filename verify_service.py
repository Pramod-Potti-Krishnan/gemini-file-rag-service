import requests
import os
import json

# Configuration
BASE_URL = "http://localhost:8000"

def test_root():
    print("Testing Root Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Failed: {e}")

def test_generate_content():
    print("\nTesting Content Generation...")
    try:
        # Note: This test assumes you have a valid store_name if you want to test RAG.
        # Otherwise it tests the standard LLM fallback.
        payload = {
            "prompt": "Summarize the document",
            "slide_type": "text",
            "context": {},
            "rag_config": {
                # "store_name": "projects/..." # Uncomment and set to test RAG
            }
        }
        response = requests.post(f"{BASE_URL}/api/v1/content/generate", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_root()
    # Note: Generate test requires a running server and valid Google Cloud credentials.
    # Uncomment to run if server is active.
    # test_generate_content()
