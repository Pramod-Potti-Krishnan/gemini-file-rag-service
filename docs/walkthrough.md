# Backend File Service Walkthrough

## Overview
The Backend Service is a stateless RAG (Retrieval-Augmented Generation) service. It generates presentation content using Google Gemini, leveraging context from a Gemini File Search Store provided by the frontend.

**Note:** File uploads and Store management are handled by the Frontend (Next.js).

## Implemented Components

### 1. API Routers
- **`routers/content.py`**:
    - `POST /api/v1/content/generate`: Generates content using RAG (if `store_name` is provided) or standard LLM.

### 2. Services
- **`services/gemini.py`**: Helper functions to interact with Google Gemini API (content generation).

### 3. Main Application
- **`main.py`**: FastAPI app entry point.

## Verification

### Prerequisites
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Set environment variables:
    - `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Service Account JSON key.
    - `GOOGLE_CLOUD_PROJECT`: Your Google Cloud Project ID.
    - `GOOGLE_CLOUD_LOCATION`: Your Google Cloud Region (e.g., `us-central1`).

### Running the Service
```bash
uvicorn main:app --reload
```

### Testing
I have provided a `verify_service.py` script to test the endpoints.
```bash
python verify_service.py
```

> [!NOTE]
> The verification script currently only tests the root endpoint by default. Uncomment `test_generate_content` in `verify_service.py` to test generation. To test RAG specifically, you must provide a valid `store_name` in the payload.
