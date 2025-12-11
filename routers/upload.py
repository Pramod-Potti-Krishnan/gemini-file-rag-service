"""
Upload Router - File upload endpoints for RAG service

Provides endpoints to:
1. Create a File Search store
2. Upload files to a store
3. List files in a store
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import tempfile
import os

from services.gemini import get_gemini_client

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateStoreRequest(BaseModel):
    session_id: str
    user_id: str
    display_name: Optional[str] = None


class CreateStoreResponse(BaseModel):
    success: bool
    store_name: str
    display_name: str
    created_at: datetime


class UploadFileResponse(BaseModel):
    success: bool
    file_name: str
    store_name: str
    file_uri: Optional[str] = None
    message: str


class ListFilesResponse(BaseModel):
    success: bool
    store_name: str
    files: List[Dict]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/store/create", response_model=CreateStoreResponse)
async def create_store(request: CreateStoreRequest):
    """
    Create a new File Search store for uploading documents.

    Returns the store_name to use for subsequent uploads and RAG queries.
    """
    try:
        client = get_gemini_client()

        display_name = request.display_name or f"Session_{request.session_id}"

        store = client.caches.create(
            model="gemini-2.0-flash",
            display_name=display_name,
            config={
                "metadata": {
                    "session_id": request.session_id,
                    "user_id": request.user_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
        )

        return CreateStoreResponse(
            success=True,
            store_name=store.name,
            display_name=display_name,
            created_at=datetime.utcnow()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create store: {str(e)}")


@router.post("/file", response_model=UploadFileResponse)
async def upload_file(
    store_name: str,
    file: UploadFile = File(...),
    display_name: Optional[str] = None
):
    """
    Upload a file to a File Search store.

    Supported file types: PDF, DOCX, TXT, CSV, XLSX, etc.
    """
    try:
        client = get_gemini_client()

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Upload to Gemini
            uploaded_file = client.files.upload(
                file=tmp_path,
                config={
                    "display_name": display_name or file.filename
                }
            )

            return UploadFileResponse(
                success=True,
                file_name=file.filename,
                store_name=store_name,
                file_uri=uploaded_file.uri if hasattr(uploaded_file, 'uri') else None,
                message=f"File '{file.filename}' uploaded successfully"
            )

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/files/{store_name}", response_model=ListFilesResponse)
async def list_files(store_name: str):
    """
    List all files in a File Search store.
    """
    try:
        client = get_gemini_client()

        # List files
        files_list = []
        for f in client.files.list():
            files_list.append({
                "name": f.name,
                "display_name": getattr(f, 'display_name', 'Unknown'),
                "uri": getattr(f, 'uri', None),
                "state": getattr(f, 'state', 'UNKNOWN'),
                "size_bytes": getattr(f, 'size_bytes', None)
            })

        return ListFilesResponse(
            success=True,
            store_name=store_name,
            files=files_list
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")
