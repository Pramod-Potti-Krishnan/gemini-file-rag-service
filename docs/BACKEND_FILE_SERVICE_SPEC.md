# Backend File Service Specification: RAG with Google Gemini File API

## Document Version: 1.0
**Last Updated:** 2025-11-25
**Target Completion:** TBD
**Owner:** Backend Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Google Gemini File API Integration](#google-gemini-file-api-integration)
4. [API Endpoints Specification](#api-endpoints-specification)
5. [Database Schema](#database-schema)
6. [RAG Workflow](#rag-workflow)
7. [Grounding & Citations](#grounding--citations)
8. [Error Handling & Fallback Strategy](#error-handling--fallback-strategy)
9. [Environment Configuration](#environment-configuration)
10. [Security & Authentication](#security--authentication)
11. [Performance & Scalability](#performance--scalability)
12. [Testing Strategy](#testing-strategy)
13. [Deployment Guide](#deployment-guide)
14. [Monitoring & Observability](#monitoring--observability)
15. [Appendix](#appendix)

---

## Executive Summary

### Overview
This document specifies a backend RAG (Retrieval-Augmented Generation) file service using **Python FastAPI** and **Google Gemini File API** to enable context-aware presentation content generation for the Deckster application.

### Key Objectives
- Accept file uploads from the Deckster frontend
- Upload files to Google Gemini File API for embedding and indexing
- Create and manage Gemini File Search stores for each user session
- Provide RAG-based content generation endpoints for the presentation builder
- Return grounded responses with citations when files are available
- Fallback to standard LLM generation when no files exist

### Technology Stack
- **Framework:** FastAPI 0.109+ (Python 3.11+)
- **AI Platform:** Google Gemini API (Gemini 2.5 Flash)
- **Database:** PostgreSQL 15+ with SQLAlchemy 2.0
- **File Storage:** Google Gemini File API (48-hour retention)
- **Authentication:** JWT tokens + API keys
- **Deployment:** Docker + Railway/GCP Cloud Run

### Success Criteria
- ✅ File uploads complete in <5 seconds for 20 MB files
- ✅ RAG retrieval returns relevant context with >80% accuracy
- ✅ Citations properly formatted and traceable to source documents
- ✅ Service handles 100+ concurrent requests
- ✅ 99.9% uptime SLA
- ✅ Graceful fallback when files unavailable

---

## Architecture Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Deckster Frontend                            │
│                   (Next.js Application)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Backend File Service                            │
│                     (FastAPI)                                    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ File Upload  │  │ Content Gen  │  │ File Mgmt    │         │
│  │ Endpoint     │  │ Endpoint     │  │ Endpoints    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └─────────┬────────┴──────────────────┘                 │
│                   ▼                                              │
│         ┌─────────────────────┐                                 │
│         │   Service Layer     │                                 │
│         │  - File Processing  │                                 │
│         │  - RAG Orchestration│                                 │
│         │  - Citation Parsing │                                 │
│         └─────────┬───────────┘                                 │
│                   │                                              │
│         ┌─────────┴───────────┐                                 │
│         ▼                     ▼                                  │
│  ┌──────────────┐      ┌──────────────┐                        │
│  │  PostgreSQL  │      │ Gemini API   │                        │
│  │  Database    │      │  Client      │                        │
│  └──────────────┘      └──────┬───────┘                        │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                                 │ gRPC/REST
                                 ▼
                    ┌────────────────────────┐
                    │  Google Gemini API     │
                    │                        │
                    │  ┌──────────────────┐  │
                    │  │ File API         │  │
                    │  │ (Upload/Storage) │  │
                    │  └──────────────────┘  │
                    │                        │
                    │  ┌──────────────────┐  │
                    │  │ File Search API  │  │
                    │  │ (RAG/Embeddings) │  │
                    │  └──────────────────┘  │
                    │                        │
                    │  ┌──────────────────┐  │
                    │  │ Generative API   │  │
                    │  │ (Content Gen)    │  │
                    │  └──────────────────┘  │
                    └────────────────────────┘
```

### Component Responsibilities

#### 1. FastAPI Application
- **Role:** HTTP API server for file operations and content generation
- **Responsibilities:**
  - Request validation and authentication
  - File upload orchestration
  - RAG workflow management
  - Response formatting with citations
  - Error handling and logging

#### 2. File Upload Service
- **Role:** Handles file uploads from frontend
- **Responsibilities:**
  - Validate file type, size, and content
  - Upload to Gemini File API
  - Create/update File Search stores
  - Store file metadata in PostgreSQL
  - Return file URIs to frontend

#### 3. Content Generation Service
- **Role:** Generates presentation content using RAG
- **Responsibilities:**
  - Check if files exist for session
  - Query Gemini File Search for relevant context
  - Generate content with grounding
  - Extract and format citations
  - Fallback to standard generation when no files

#### 4. Gemini API Client
- **Role:** Interface with Google Gemini services
- **Responsibilities:**
  - File upload to Gemini File API
  - File Search store management
  - Semantic search queries
  - Content generation requests
  - Response parsing and error handling

#### 5. PostgreSQL Database
- **Role:** Persistent storage for metadata
- **Responsibilities:**
  - Store file metadata (name, size, type, URIs)
  - Map files to user sessions
  - Track File Search store IDs
  - Log API usage and errors

---

## Google Gemini File API Integration

### Supported File Formats

Based on official Gemini documentation, the File API supports:

#### Document Formats
- **PDF:** `application/pdf`
- **Microsoft Word:** `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- **Text:** `text/plain`, `text/markdown`, `text/html`, `text/css`
- **Rich Text:** `application/rtf`

#### Spreadsheet Formats
- **Excel:** `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **CSV/TSV:** `text/csv`, `text/tab-separated-values`

#### Presentation Formats
- **PowerPoint:** `application/vnd.ms-powerpoint`, `application/vnd.openxmlformats-officedocument.presentationml.presentation`

#### Data Formats
- **JSON:** `application/json`
- **XML:** `application/xml`, `text/xml`
- **YAML:** `application/x-yaml`, `text/yaml`

#### Code Files
- **JavaScript/TypeScript:** `text/javascript`, `application/javascript`, `text/typescript`
- **Python:** `text/x-python`, `application/x-python-code`
- **Java:** `text/x-java`
- **Go:** `text/x-go`
- **Rust:** `text/x-rust`
- **C/C++:** `text/x-c`, `text/x-c++`

#### Image Formats (for OCR/Visual Context)
- **PNG:** `image/png`
- **JPEG:** `image/jpeg`
- **WebP:** `image/webp`

### File Size & Storage Limits

| Limit Type | Value | Notes |
|------------|-------|-------|
| Per-file maximum | 2 GB | For Files API |
| Per-file maximum (File Search) | 100 MB | Recommended for optimal performance |
| Total storage (Free tier) | 1 GB | Per Google Cloud project |
| Total storage (Tier 1) | 10 GB | Paid tier |
| Total storage (Tier 2) | 100 GB | Paid tier |
| Total storage (Tier 3) | 1 TB | Paid tier |
| Per File Search store | 20 GB | Recommended for best latency |
| File retention | 48 hours | Auto-deletion after upload |

### Gemini File Search Overview

**What is File Search?**
- Fully managed RAG system built into Gemini API
- Automatically chunks, embeds, and indexes documents
- Performs semantic search for relevant context
- Returns citations with grounding metadata

**Key Features:**
- **Automatic Chunking:** Optimal chunk sizes determined by Gemini
- **Semantic Embeddings:** High-quality embeddings at $0.15 per 1M tokens
- **Grounding Metadata:** Citations specify source documents and page numbers
- **Metadata Filtering:** Filter searches by custom metadata
- **Free Storage:** No charge for storing indexed documents

**Supported Models:**
- `gemini-2.5-pro`
- `gemini-2.5-flash` (recommended for speed)
- `gemini-2.5-flash-lite`

### File Upload Methods

#### Method 1: Direct Upload to File Search Store
**Use case:** When you want to upload and index in one operation

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_API_KEY)

# Upload file directly to File Search store
operation = client.file_search_stores.upload_to_file_search_store(
    file='path/to/document.pdf',
    file_search_store_name=store_name,
    display_name='Q4 Sales Report',
    metadata={
        'session_id': session_id,
        'user_id': user_id,
        'uploaded_by': 'Deckster Frontend'
    }
)

# Wait for processing to complete
result = operation.result()
print(f"File URI: {result.file.name}")
```

#### Method 2: Two-Step Upload (Files API → Import)
**Use case:** When you need to use the same file in multiple stores

```python
# Step 1: Upload to Files API
file = client.files.upload(file='path/to/document.pdf')
print(f"File uploaded: {file.name}")

# Step 2: Import into File Search store
operation = client.file_search_stores.import_file(
    file_search_store_name=store_name,
    file_name=file.name
)
result = operation.result()
```

### Creating File Search Stores

**One store per session** (recommended approach):

```python
# Create File Search store for a session
store = client.file_search_stores.create(
    display_name=f"Session_{session_id}",
    metadata={
        'session_id': session_id,
        'user_id': user_id,
        'created_at': datetime.utcnow().isoformat()
    }
)

print(f"Store created: {store.name}")
# Store name format: "fileSearchStores/{store_id}"
```

### Performing RAG Queries

```python
from google.genai import types

# Query with File Search
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='What were the key findings in the sales report?',
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                file_search=types.FileSearchTool(
                    file_search_store_names=[store.name]
                )
            )
        ]
    )
)

# Access response with grounding
print(response.text)

# Access citations
grounding_metadata = response.candidates[0].grounding_metadata
if grounding_metadata:
    for chunk in grounding_metadata.grounding_chunks:
        print(f"Source: {chunk.web.title}")
        print(f"Content: {chunk.content}")
```

---

## API Endpoints Specification

### Base URL
- **Development:** `http://localhost:8000`
- **Production:** `https://deckster-file-service.up.railway.app`

### Authentication
All endpoints require authentication via:
- **JWT Token** in `Authorization: Bearer <token>` header
- **API Key** in `X-API-Key` header (for service-to-service calls)

---

### 1. File Upload Endpoint

**POST** `/api/v1/files/upload`

**Description:** Upload a file from the frontend, process it, and upload to Gemini File API.

**Request Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data
```

**Request Body (multipart/form-data):**
```
file: <binary file data>
session_id: string (UUID)
user_id: string (email or UUID)
```

**Example cURL:**
```bash
curl -X POST https://deckster-file-service.up.railway.app/api/v1/files/upload \
  -H "Authorization: Bearer eyJhbGc..." \
  -F "file=@/path/to/document.pdf" \
  -F "session_id=abc-123-def" \
  -F "user_id=user@example.com"
```

**Response (200 OK):**
```json
{
  "file_id": "f8d7c6b5-4321-4321-8765-1234567890ab",
  "file_name": "Q4_Sales_Report.pdf",
  "file_size": 2457600,
  "file_type": "application/pdf",
  "gemini_file_uri": "files/abc123xyz789",
  "gemini_file_id": "abc123xyz789",
  "file_search_store_id": "fileSearchStores/store_456",
  "uploaded_at": "2025-11-25T10:30:00Z",
  "status": "indexed"
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "File size exceeds 20 MB limit",
  "error_code": "FILE_SIZE_EXCEEDED",
  "max_size_mb": 20,
  "actual_size_mb": 25.3
}
```

**Response (409 Conflict):**
```json
{
  "detail": "Maximum 5 files per session",
  "error_code": "MAX_FILES_EXCEEDED",
  "current_count": 5,
  "max_count": 5
}
```

**Response (500 Internal Server Error):**
```json
{
  "detail": "Failed to upload file to Gemini API",
  "error_code": "GEMINI_UPLOAD_FAILED",
  "gemini_error": "Service unavailable"
}
```

**Implementation:**
```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from google import genai
from sqlalchemy.orm import Session
import os

router = APIRouter()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validate file
    if file.size > 20 * 1024 * 1024:  # 20 MB
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "File size exceeds 20 MB limit",
                "error_code": "FILE_SIZE_EXCEEDED",
                "max_size_mb": 20,
                "actual_size_mb": round(file.size / 1024 / 1024, 1)
            }
        )

    # 2. Check file count limit
    file_count = db.query(UploadedFile).filter_by(session_id=session_id).count()
    if file_count >= 5:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "Maximum 5 files per session",
                "error_code": "MAX_FILES_EXCEEDED",
                "current_count": file_count,
                "max_count": 5
            }
        )

    # 3. Save file temporarily
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        # 4. Get or create File Search store for session
        store = get_or_create_file_search_store(session_id, user_id, db)

        # 5. Upload to Gemini File API
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        operation = client.file_search_stores.upload_to_file_search_store(
            file=temp_path,
            file_search_store_name=store.gemini_store_name,
            display_name=file.filename,
            metadata={
                "session_id": session_id,
                "user_id": user_id,
                "original_filename": file.filename
            }
        )

        result = operation.result()

        # 6. Store metadata in database
        uploaded_file = UploadedFile(
            session_id=session_id,
            user_id=user_id,
            file_name=file.filename,
            file_size=file.size,
            file_type=file.content_type,
            gemini_file_uri=result.file.name,
            gemini_file_id=result.file.name.split("/")[-1],
            file_search_store_id=store.gemini_store_name
        )

        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)

        return {
            "file_id": str(uploaded_file.id),
            "file_name": uploaded_file.file_name,
            "file_size": uploaded_file.file_size,
            "file_type": uploaded_file.file_type,
            "gemini_file_uri": uploaded_file.gemini_file_uri,
            "gemini_file_id": uploaded_file.gemini_file_id,
            "file_search_store_id": uploaded_file.file_search_store_id,
            "uploaded_at": uploaded_file.uploaded_at.isoformat(),
            "status": "indexed"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "detail": "Failed to upload file to Gemini API",
                "error_code": "GEMINI_UPLOAD_FAILED",
                "gemini_error": str(e)
            }
        )

    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
```

---

### 2. Content Generation Endpoint (RAG)

**POST** `/api/v1/content/generate`

**Description:** Generate presentation content using RAG if files exist, otherwise use standard LLM.

**Request Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "session_id": "abc-123-def",
  "user_id": "user@example.com",
  "prompt": "Create a slide about Q4 sales performance with key metrics",
  "slide_type": "data_visualization",
  "context": {
    "presentation_title": "Q4 Business Review",
    "slide_number": 3,
    "total_slides": 10
  }
}
```

**Response (200 OK) - With Files:**
```json
{
  "content": {
    "title": "Q4 Sales Performance",
    "bullet_points": [
      "Total revenue: $2.4M (up 15% YoY)",
      "New customers acquired: 450",
      "Customer retention rate: 92%"
    ],
    "speaker_notes": "Focus on the significant YoY growth...",
    "data_visualization": {
      "type": "bar_chart",
      "data": {
        "labels": ["Q1", "Q2", "Q3", "Q4"],
        "values": [1.8, 2.0, 2.2, 2.4]
      }
    }
  },
  "grounding": {
    "used_files": true,
    "file_count": 2,
    "citations": [
      {
        "file_name": "Q4_Sales_Report.pdf",
        "file_uri": "files/abc123",
        "chunks": [
          {
            "content": "Total Q4 revenue reached $2.4M, representing a 15% increase year-over-year.",
            "page": 3,
            "confidence": 0.95
          }
        ]
      },
      {
        "file_name": "Customer_Metrics.xlsx",
        "file_uri": "files/def456",
        "chunks": [
          {
            "content": "New customer acquisition: 450 customers in Q4",
            "page": 1,
            "confidence": 0.92
          }
        ]
      }
    ]
  },
  "generated_at": "2025-11-25T10:35:00Z",
  "model_used": "gemini-2.5-flash",
  "generation_method": "rag"
}
```

**Response (200 OK) - Without Files (Fallback):**
```json
{
  "content": {
    "title": "Q4 Sales Performance",
    "bullet_points": [
      "Review quarterly sales metrics",
      "Analyze growth trends",
      "Identify key performance drivers"
    ],
    "speaker_notes": "Generic content generated without specific data..."
  },
  "grounding": {
    "used_files": false,
    "file_count": 0,
    "citations": []
  },
  "generated_at": "2025-11-25T10:35:00Z",
  "model_used": "gemini-2.5-flash",
  "generation_method": "standard_llm"
}
```

**Response (500 Internal Server Error):**
```json
{
  "detail": "Content generation failed",
  "error_code": "GENERATION_FAILED",
  "error_message": "Gemini API timeout"
}
```

**Implementation:**
```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from google import genai
from google.genai import types

router = APIRouter()

class ContentGenerationRequest(BaseModel):
    session_id: str
    user_id: str
    prompt: str
    slide_type: str
    context: dict = {}

@router.post("/generate")
async def generate_content(
    request: ContentGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Check if files exist for session
    files = db.query(UploadedFile).filter_by(session_id=request.session_id).all()

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    if files and len(files) > 0:
        # RAG-based generation
        try:
            # Get File Search store for session
            store = db.query(FileSearchStore).filter_by(session_id=request.session_id).first()

            if not store:
                raise HTTPException(status_code=404, detail="File Search store not found")

            # Generate content with File Search
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{request.prompt}\n\nContext: {request.context}",
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearchTool(
                                file_search_store_names=[store.gemini_store_name]
                            )
                        )
                    ],
                    temperature=0.7,
                    max_output_tokens=2048
                )
            )

            # Parse response
            content = parse_slide_content(response.text, request.slide_type)

            # Extract citations
            citations = extract_citations(response, files)

            return {
                "content": content,
                "grounding": {
                    "used_files": True,
                    "file_count": len(files),
                    "citations": citations
                },
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": "gemini-2.5-flash",
                "generation_method": "rag"
            }

        except Exception as e:
            # Fallback to standard generation on error
            print(f"RAG generation failed: {e}. Falling back to standard LLM.")
            pass

    # Fallback: Standard LLM generation (no files)
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{request.prompt}\n\nContext: {request.context}",
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048
            )
        )

        content = parse_slide_content(response.text, request.slide_type)

        return {
            "content": content,
            "grounding": {
                "used_files": False,
                "file_count": 0,
                "citations": []
            },
            "generated_at": datetime.utcnow().isoformat(),
            "model_used": "gemini-2.5-flash",
            "generation_method": "standard_llm"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "detail": "Content generation failed",
                "error_code": "GENERATION_FAILED",
                "error_message": str(e)
            }
        )
```

---

### 3. List Session Files

**GET** `/api/v1/files/session/{session_id}`

**Description:** Get all files uploaded for a specific session.

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**
```json
{
  "session_id": "abc-123-def",
  "file_count": 3,
  "files": [
    {
      "file_id": "f8d7c6b5-4321-4321-8765-1234567890ab",
      "file_name": "Q4_Sales_Report.pdf",
      "file_size": 2457600,
      "file_type": "application/pdf",
      "gemini_file_uri": "files/abc123",
      "uploaded_at": "2025-11-25T10:30:00Z"
    },
    {
      "file_id": "a1b2c3d4-5678-9012-3456-7890abcdef12",
      "file_name": "Customer_Data.xlsx",
      "file_size": 512000,
      "file_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "gemini_file_uri": "files/def456",
      "uploaded_at": "2025-11-25T10:32:00Z"
    }
  ]
}
```

**Implementation:**
```python
@router.get("/session/{session_id}")
async def list_session_files(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    files = db.query(UploadedFile).filter_by(session_id=session_id).all()

    return {
        "session_id": session_id,
        "file_count": len(files),
        "files": [
            {
                "file_id": str(f.id),
                "file_name": f.file_name,
                "file_size": f.file_size,
                "file_type": f.file_type,
                "gemini_file_uri": f.gemini_file_uri,
                "uploaded_at": f.uploaded_at.isoformat()
            }
            for f in files
        ]
    }
```

---

### 4. Delete File

**DELETE** `/api/v1/files/{file_id}`

**Description:** Delete a file from the database and optionally from Gemini File API.

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "file_id": "f8d7c6b5-4321-4321-8765-1234567890ab",
  "deleted_at": "2025-11-25T11:00:00Z"
}
```

**Implementation:**
```python
@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file = db.query(UploadedFile).filter_by(id=file_id).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Optional: Delete from Gemini (files auto-delete after 48 hours)
    # client.files.delete(name=file.gemini_file_uri)

    db.delete(file)
    db.commit()

    return {
        "success": True,
        "file_id": file_id,
        "deleted_at": datetime.utcnow().isoformat()
    }
```

---

### 5. Health Check

**GET** `/health`

**Description:** Check service health and dependencies.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-25T10:00:00Z",
  "version": "1.0.0",
  "dependencies": {
    "database": "connected",
    "gemini_api": "reachable"
  }
}
```

---

## Database Schema

### PostgreSQL Tables

#### 1. uploaded_files

```sql
CREATE TABLE uploaded_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    gemini_file_uri TEXT NOT NULL,
    gemini_file_id VARCHAR(255),
    file_search_store_id VARCHAR(255),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_uploaded_at (uploaded_at DESC)
);
```

#### 2. file_search_stores

```sql
CREATE TABLE file_search_stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    gemini_store_name VARCHAR(500) NOT NULL,
    gemini_store_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id)
);
```

#### 3. content_generations

```sql
CREATE TABLE content_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    prompt TEXT NOT NULL,
    slide_type VARCHAR(100),
    content JSONB NOT NULL,
    grounding_metadata JSONB,
    generation_method VARCHAR(50) NOT NULL,  -- 'rag' or 'standard_llm'
    model_used VARCHAR(100) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_session_id (session_id),
    INDEX idx_generated_at (generated_at DESC)
);
```

### SQLAlchemy Models

**File:** `models/database.py`

```python
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    file_name = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(100), nullable=False)
    gemini_file_uri = Column(Text, nullable=False)
    gemini_file_id = Column(String(255))
    file_search_store_id = Column(String(255))
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)

class FileSearchStore(Base):
    __tablename__ = "file_search_stores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    gemini_store_name = Column(String(500), nullable=False)
    gemini_store_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ContentGeneration(Base):
    __tablename__ = "content_generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    slide_type = Column(String(100))
    content = Column(JSON, nullable=False)
    grounding_metadata = Column(JSON)
    generation_method = Column(String(50), nullable=False)
    model_used = Column(String(100), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
```

---

## RAG Workflow

### Complete RAG Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. File Upload Phase                                             │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────┐
    │ User uploads file via frontend        │
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │ Backend receives file + session_id   │
    │ - Validate file (size, type)         │
    │ - Check file count limit (5 max)     │
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │ Get or create File Search store      │
    │ for session_id                       │
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │ Upload file to Gemini File API       │
    │ - Direct upload to File Search store │
    │ - Gemini auto-chunks and embeds      │
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │ Store metadata in PostgreSQL         │
    │ - File URI, name, size               │
    │ - Link to session_id                 │
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │ Return file metadata to frontend     │
    └──────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. Content Generation Phase                                     │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────┐
    │ Director AI requests slide content   │
    │ - Sends prompt + session_id          │
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │ Check if files exist for session     │
    └──────────────┬───────────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
    ┌─────────┐         ┌─────────┐
    │ Files   │         │ No Files│
    │ Exist   │         │         │
    └────┬────┘         └────┬────┘
         │                   │
         ▼                   ▼
    ┌──────────────┐    ┌──────────────┐
    │ RAG Mode     │    │ Fallback     │
    │              │    │ Mode         │
    └──────┬───────┘    └──────┬───────┘
           │                   │
           ▼                   ▼
    ┌─────────────────────────────────┐
    │ Query Gemini with File Search   │
    │ - Semantic search in store      │
    │ - Retrieve relevant chunks      │
    │ - Generate grounded content     │
    │ - Extract citations             │
    └─────────────┬───────────────────┘
           │      │
           │      └────────────────────┐
           ▼                           ▼
    ┌─────────────────┐         ┌──────────────┐
    │ Standard LLM    │         │ Return       │
    │ Generation      │         │ Content +    │
    │ (no grounding)  │         │ Citations    │
    └─────────┬───────┘         └──────────────┘
              │
              └──────────┐
                         ▼
                  ┌──────────────┐
                  │ Return       │
                  │ Content Only │
                  └──────────────┘
```

### Step-by-Step RAG Implementation

#### Step 1: File Upload and Indexing

```python
async def upload_and_index_file(
    file_path: str,
    session_id: str,
    user_id: str,
    file_name: str,
    file_size: int,
    file_type: str,
    db: Session
) -> UploadedFile:
    """
    Upload file to Gemini and index in File Search store.
    """
    # Get or create File Search store
    store = get_or_create_file_search_store(session_id, user_id, db)

    # Upload to Gemini File API
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    operation = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store.gemini_store_name,
        display_name=file_name,
        metadata={
            "session_id": session_id,
            "user_id": user_id,
            "original_filename": file_name
        }
    )

    # Wait for indexing to complete
    result = operation.result()

    # Store in database
    uploaded_file = UploadedFile(
        session_id=session_id,
        user_id=user_id,
        file_name=file_name,
        file_size=file_size,
        file_type=file_type,
        gemini_file_uri=result.file.name,
        gemini_file_id=result.file.name.split("/")[-1],
        file_search_store_id=store.gemini_store_name
    )

    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)

    return uploaded_file
```

#### Step 2: RAG Content Generation

```python
from google.genai import types

async def generate_content_with_rag(
    prompt: str,
    session_id: str,
    slide_type: str,
    context: dict,
    db: Session
) -> dict:
    """
    Generate content using RAG if files exist.
    """
    # Check for files
    files = db.query(UploadedFile).filter_by(session_id=session_id).all()

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    if files:
        # Get File Search store
        store = db.query(FileSearchStore).filter_by(session_id=session_id).first()

        # Generate with File Search
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=build_prompt(prompt, slide_type, context),
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearchTool(
                            file_search_store_names=[store.gemini_store_name]
                        )
                    )
                ],
                temperature=0.7,
                max_output_tokens=2048
            )
        )

        # Extract content and citations
        content = parse_slide_content(response.text, slide_type)
        citations = extract_citations(response, files)

        return {
            "content": content,
            "grounding": {
                "used_files": True,
                "file_count": len(files),
                "citations": citations
            },
            "generation_method": "rag"
        }
    else:
        # Fallback to standard LLM
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=build_prompt(prompt, slide_type, context),
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048
            )
        )

        content = parse_slide_content(response.text, slide_type)

        return {
            "content": content,
            "grounding": {
                "used_files": False,
                "file_count": 0,
                "citations": []
            },
            "generation_method": "standard_llm"
        }
```

#### Step 3: Citation Extraction

```python
def extract_citations(response, files: list) -> list:
    """
    Extract citations from Gemini response grounding metadata.
    """
    citations = []

    grounding_metadata = response.candidates[0].grounding_metadata

    if not grounding_metadata:
        return citations

    # Map file URIs to file objects
    file_map = {f.gemini_file_uri: f for f in files}

    for chunk in grounding_metadata.grounding_chunks:
        if hasattr(chunk, 'retrieved_context'):
            file_uri = chunk.retrieved_context.uri

            if file_uri in file_map:
                file_obj = file_map[file_uri]

                citation = {
                    "file_name": file_obj.file_name,
                    "file_uri": file_uri,
                    "chunks": [{
                        "content": chunk.retrieved_context.text,
                        "confidence": getattr(chunk, 'confidence_score', None)
                    }]
                }

                citations.append(citation)

    return citations
```

---

## Grounding & Citations

### Citation Data Structure

```python
{
  "citations": [
    {
      "file_name": "Q4_Sales_Report.pdf",
      "file_uri": "files/abc123xyz789",
      "chunks": [
        {
          "content": "Total Q4 revenue reached $2.4M, representing a 15% increase year-over-year.",
          "page": 3,
          "confidence": 0.95,
          "start_index": 0,
          "end_index": 85
        },
        {
          "content": "Key growth drivers included new product launches and market expansion.",
          "page": 5,
          "confidence": 0.88
        }
      ]
    }
  ]
}
```

### Displaying Citations in Frontend

**Example UI Pattern:**
```
┌────────────────────────────────────────────────────┐
│ Slide Content:                                     │
│                                                    │
│ Q4 Revenue: $2.4M (↑15% YoY) [1]                  │
│ New Customers: 450 [2]                            │
│                                                    │
│ Sources:                                           │
│ [1] Q4_Sales_Report.pdf, page 3                   │
│ [2] Customer_Metrics.xlsx, page 1                 │
└────────────────────────────────────────────────────┘
```

---

## Error Handling & Fallback Strategy

### Error Scenarios

| Scenario | Error Code | HTTP Status | Fallback Action |
|----------|-----------|-------------|-----------------|
| File size > 20 MB | FILE_SIZE_EXCEEDED | 400 | Reject upload, show error |
| File type unsupported | INVALID_FILE_TYPE | 400 | Reject upload, show error |
| Max files (5) reached | MAX_FILES_EXCEEDED | 409 | Reject upload, show error |
| Gemini API timeout | GEMINI_TIMEOUT | 500 | Retry 3x, then fallback to standard LLM |
| Gemini API quota exceeded | GEMINI_QUOTA_EXCEEDED | 429 | Wait + retry, or fallback |
| File Search store not found | STORE_NOT_FOUND | 404 | Create new store |
| No files for session | NO_FILES | 200 | Use standard LLM (not an error) |
| Database connection error | DB_CONNECTION_ERROR | 503 | Retry, then return 503 |

### Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def upload_to_gemini_with_retry(file_path, store_name):
    """
    Upload file with automatic retry on transient errors.
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    operation = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store_name
    )

    return operation.result()
```

### Graceful Degradation

```python
async def generate_content_with_fallback(prompt, session_id, db):
    """
    Try RAG first, fallback to standard LLM on any error.
    """
    try:
        # Attempt RAG generation
        return await generate_content_with_rag(prompt, session_id, db)
    except Exception as e:
        logger.warning(f"RAG generation failed: {e}. Falling back to standard LLM.")

        # Fallback to standard LLM
        try:
            return await generate_content_standard(prompt)
        except Exception as fallback_error:
            logger.error(f"Fallback generation also failed: {fallback_error}")
            raise HTTPException(
                status_code=500,
                detail="Content generation failed"
            )
```

---

## Environment Configuration

### Required Environment Variables

**File:** `.env`

```bash
# Application
APP_NAME=deckster-file-service
APP_VERSION=1.0.0
ENVIRONMENT=production  # or development, staging

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/deckster_files
# For connection pooling:
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash  # or gemini-2.5-pro

# File Upload Limits
MAX_FILE_SIZE_MB=20
MAX_FILES_PER_SESSION=5

# Authentication
JWT_SECRET=your_jwt_secret_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Keys (for service-to-service auth)
API_KEY_FRONTEND=frontend_api_key_here
API_KEY_DIRECTOR=director_api_key_here

# CORS
CORS_ORIGINS=https://deckster.xyz,http://localhost:3000

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json  # or text

# Monitoring
SENTRY_DSN=https://your_sentry_dsn_here
ENABLE_METRICS=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
```

### Configuration Management

**File:** `config/settings.py`

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application
    app_name: str = "deckster-file-service"
    app_version: str = "1.0.0"
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Gemini API
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"

    # File Upload
    max_file_size_mb: int = 20
    max_files_per_session: int = 5

    # Authentication
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # API Keys
    api_key_frontend: str
    api_key_director: str

    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Monitoring
    sentry_dsn: str | None = None
    enable_metrics: bool = True

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Security & Authentication

### JWT Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

security = HTTPBearer()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

        return {"user_id": user_id, "email": payload.get("email")}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

### Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

@router.post("/upload")
@limiter.limit("10/minute")
async def upload_file(request: Request, ...):
    # Upload logic
    pass
```

---

## Performance & Scalability

### Optimization Strategies

1. **Database Connection Pooling:**
   ```python
   from sqlalchemy import create_engine
   from sqlalchemy.pool import QueuePool

   engine = create_engine(
       settings.database_url,
       poolclass=QueuePool,
       pool_size=20,
       max_overflow=10,
       pool_pre_ping=True  # Check connection before use
   )
   ```

2. **Async File Processing:**
   ```python
   import aiofiles

   async def save_file_async(file: UploadFile, path: str):
       async with aiofiles.open(path, 'wb') as f:
           await f.write(await file.read())
   ```

3. **Caching File Search Store Lookups:**
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def get_file_search_store_cached(session_id: str):
       return db.query(FileSearchStore).filter_by(session_id=session_id).first()
   ```

4. **Background Tasks for Cleanup:**
   ```python
   from fastapi import BackgroundTasks

   @router.post("/upload")
   async def upload_file(..., background_tasks: BackgroundTasks):
       # Upload logic

       background_tasks.add_task(cleanup_temp_file, temp_path)

       return response
   ```

### Horizontal Scaling

- Deploy multiple instances behind a load balancer
- Use stateless design (all state in database)
- Share database connection pool across instances
- Use Redis for distributed caching (optional)

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_file_upload.py`

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_upload_file_success():
    with open("tests/fixtures/test.pdf", "rb") as f:
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"session_id": "test-123", "user_id": "user@test.com"},
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 200
    assert "gemini_file_uri" in response.json()

def test_upload_file_too_large():
    # Test file size validation
    pass

def test_upload_file_invalid_type():
    # Test file type validation
    pass
```

### Integration Tests

```python
def test_rag_generation_with_files():
    # Upload file
    # Generate content
    # Verify citations present
    pass

def test_fallback_without_files():
    # Generate content without files
    # Verify standard LLM used
    pass
```

---

## Deployment Guide

### Docker Configuration

**File:** `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/deckster
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=deckster
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Railway Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

---

## Monitoring & Observability

### Logging

```python
import logging
import structlog

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
)

logger = structlog.get_logger()

@router.post("/upload")
async def upload_file(...):
    logger.info("file_upload_started", session_id=session_id, file_name=file.filename)

    # Upload logic

    logger.info("file_upload_completed", file_id=uploaded_file.id)
```

### Metrics

```python
from prometheus_client import Counter, Histogram

upload_counter = Counter('file_uploads_total', 'Total file uploads')
generation_duration = Histogram('content_generation_duration_seconds', 'Content generation duration')

@router.post("/upload")
async def upload_file(...):
    upload_counter.inc()
    # Logic
```

---

## Appendix

### A. Example Prompts for Slide Generation

```python
PROMPT_TEMPLATES = {
    "title_slide": """
        Create a compelling title slide with:
        - Main title based on: {topic}
        - Subtitle that captures the essence
        - Use data from uploaded files if available
    """,

    "data_visualization": """
        Create a data visualization slide:
        - Extract numerical data from uploaded files
        - Choose appropriate chart type (bar, line, pie)
        - Add insightful title and key takeaways
        Topic: {topic}
    """,

    "bullet_points": """
        Create a bullet point slide about {topic}:
        - 3-5 concise bullet points
        - Use facts from uploaded documents
        - Include speaker notes
    """
}
```

### B. File Type to MIME Type Mapping

```python
MIME_TYPE_MAP = {
    # Documents
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
    '.md': 'text/markdown',

    # Spreadsheets
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.csv': 'text/csv',

    # Presentations
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',

    # Data
    '.json': 'application/json',
    '.xml': 'application/xml',
    '.yaml': 'application/x-yaml',

    # Images
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg'
}
```

---

**Document End**
