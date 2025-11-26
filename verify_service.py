import requests
import os
import json

# Configuration
BASE_URL = "http://localhost:8000"
SESSION_ID = "test-session-123"
USER_ID = "test-user-456"

def test_root():
    print("Testing Root Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Failed: {e}")

def test_upload_file():
    print("\nTesting File Upload...")
    # Create a dummy file
    with open("test_doc.txt", "w") as f:
        f.write("This is a test document for the Deckster backend file service. It contains information about Q4 sales.")
    
    try:
        with open("test_doc.txt", "rb") as f:
            files = {"file": f}
            data = {
                "session_id": SESSION_ID,
                "user_id": USER_ID
            }
            response = requests.post(f"{BASE_URL}/api/v1/files/upload", files=files, data=data)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Failed: {e}")
    finally:
        if os.path.exists("test_doc.txt"):
            os.remove("test_doc.txt")

def test_list_files():
    print("\nTesting List Files...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/files/session/{SESSION_ID}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Failed: {e}")

def test_generate_content():
    print("\nTesting Content Generation...")
    try:
        payload = {
            "session_id": SESSION_ID,
            "user_id": USER_ID,
            "prompt": "Summarize the document",
            "slide_type": "text",
            "context": {}
        }
        response = requests.post(f"{BASE_URL}/api/v1/content/generate", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_root()
    # Note: Upload and Generate tests require a running server and valid Google Cloud credentials.
    # Ensure GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT, and GOOGLE_CLOUD_LOCATION are set.
    # Uncomment to run if server is active.
    # test_upload_file() 
    # test_list_files()
    # test_generate_content()
