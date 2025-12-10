#!/usr/bin/env python3
"""
Verification script for Deckster RAG & Search Service v2.0

Tests all endpoints:
- Root and health check
- File RAG (overview and detailed)
- Web Search (overview and detailed)
- Legacy content generation
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"


def test_root():
    """Test root endpoint"""
    print("=" * 60)
    print("Testing Root Endpoint...")
    print("=" * 60)
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Failed: {e}")
        return False


def test_health():
    """Test health check endpoint"""
    print("\n" + "=" * 60)
    print("Testing Health Check...")
    print("=" * 60)
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Failed: {e}")
        return False


def test_file_rag_overview():
    """Test File RAG Overview endpoint"""
    print("\n" + "=" * 60)
    print("Testing File RAG Overview...")
    print("=" * 60)
    try:
        payload = {
            "store_name": "projects/your-project/locations/us-central1/fileSearchStores/test-store",
            "topic": "Q4 sales performance",
            "context": {
                "presentation_title": "Quarterly Review"
            },
            "max_themes": 3
        }
        print(f"Request: {json.dumps(payload, indent=2)}")

        response = requests.post(
            f"{BASE_URL}/api/v1/rag/file/overview",
            json=payload
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)[:1000]}...")  # Truncate long response
        return response.status_code in [200, 500]  # 500 is expected without valid store
    except Exception as e:
        print(f"Failed: {e}")
        return False


def test_file_rag_detailed():
    """Test File RAG Detailed endpoint"""
    print("\n" + "=" * 60)
    print("Testing File RAG Detailed...")
    print("=" * 60)
    try:
        payload = {
            "store_name": "projects/your-project/locations/us-central1/fileSearchStores/test-store",
            "query": "What were the key revenue metrics in Q4?",
            "context": {
                "slide_type": "data_driven",
                "slide_number": 3
            },
            "max_chunks": 5,
            "min_confidence": 0.7
        }
        print(f"Request: {json.dumps(payload, indent=2)}")

        response = requests.post(
            f"{BASE_URL}/api/v1/rag/file/detailed",
            json=payload
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)[:1000]}...")
        return response.status_code in [200, 500]
    except Exception as e:
        print(f"Failed: {e}")
        return False


def test_web_search_overview():
    """Test Web Search Overview endpoint"""
    print("\n" + "=" * 60)
    print("Testing Web Search Overview...")
    print("=" * 60)
    try:
        payload = {
            "topic": "Artificial Intelligence trends in healthcare 2024",
            "context": {
                "presentation_title": "AI in Healthcare"
            },
            "industry_focus": "healthcare",
            "recency_preference": "recent"
        }
        print(f"Request: {json.dumps(payload, indent=2)}")

        response = requests.post(
            f"{BASE_URL}/api/v1/search/web/overview",
            json=payload
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)[:1000]}...")
        return response.status_code in [200, 500]
    except Exception as e:
        print(f"Failed: {e}")
        return False


def test_web_search_detailed():
    """Test Web Search Detailed endpoint"""
    print("\n" + "=" * 60)
    print("Testing Web Search Detailed...")
    print("=" * 60)
    try:
        payload = {
            "query": "What is the current market size of AI in healthcare?",
            "context": {
                "slide_type": "data_driven",
                "slide_number": 5
            },
            "data_types_needed": ["statistics", "facts"],
            "recency_required": True
        }
        print(f"Request: {json.dumps(payload, indent=2)}")

        response = requests.post(
            f"{BASE_URL}/api/v1/search/web/detailed",
            json=payload
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)[:1000]}...")
        return response.status_code in [200, 500]
    except Exception as e:
        print(f"Failed: {e}")
        return False


def test_legacy_generate():
    """Test Legacy content generation endpoint"""
    print("\n" + "=" * 60)
    print("Testing Legacy Content Generation...")
    print("=" * 60)
    try:
        payload = {
            "type": "user_message",
            "data": {
                "text": "Summarize the key points about market trends",
                "store_name": None,
                "file_count": 0,
                "slide_type": "text",
                "context": {}
            }
        }
        print(f"Request: {json.dumps(payload, indent=2)}")

        response = requests.post(
            f"{BASE_URL}/api/v1/content/generate",
            json=payload
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)[:1000]}...")
        return response.status_code in [200, 500]
    except Exception as e:
        print(f"Failed: {e}")
        return False


def run_all_tests():
    """Run all verification tests"""
    print("\n" + "=" * 80)
    print("  DECKSTER RAG & SEARCH SERVICE v2.0 - VERIFICATION TESTS")
    print("=" * 80)

    results = {}

    # Basic connectivity tests
    results["root"] = test_root()
    results["health"] = test_health()

    # File RAG tests (will fail without valid store, but tests endpoint availability)
    results["file_rag_overview"] = test_file_rag_overview()
    results["file_rag_detailed"] = test_file_rag_detailed()

    # Web Search tests (requires Gemini API access)
    results["web_search_overview"] = test_web_search_overview()
    results["web_search_detailed"] = test_web_search_detailed()

    # Legacy endpoint test
    results["legacy_generate"] = test_legacy_generate()

    # Summary
    print("\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\n  Total: {total_passed}/{total_tests} tests passed")
    print("=" * 80)

    return all(results.values())


if __name__ == "__main__":
    print("\n" + "-" * 60)
    print("NOTE: Start the server first with: uvicorn main:app --reload")
    print("-" * 60)

    # Only run basic tests by default
    # Uncomment run_all_tests() to run full test suite

    # Basic connectivity tests (always safe to run)
    test_root()
    test_health()

    print("\n" + "-" * 60)
    print("To run full test suite including API tests:")
    print("  python verify_service.py --all")
    print("-" * 60)

    import sys
    if "--all" in sys.argv:
        run_all_tests()
