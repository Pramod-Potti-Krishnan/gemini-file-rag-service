from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import os
from typing import List

from ..database import get_db
from ..models import UploadedFile, FileSearchStore
from ..schemas import UploadedFileResponse, SessionFilesResponse
from ..services import gemini

router = APIRouter(
    prefix="/api/v1/files",
    tags=["files"]
)

def get_or_create_file_search_store(session_id: str, user_id: str, db: Session):
    store = db.query(FileSearchStore).filter_by(session_id=session_id).first()
    if not store:
        try:
            gemini_store = gemini.create_file_search_store(session_id, user_id)
            store = FileSearchStore(
                session_id=session_id,
                user_id=user_id,
                gemini_store_name=gemini_store.name
            )
            db.add(store)
            db.commit()
            db.refresh(store)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create Gemini store: {str(e)}")
    return store

@router.post("/upload", response_model=UploadedFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Validate file size
    # Note: UploadFile.size is not always available depending on backend, 
    # but we can check after reading or using spooled file. 
    # For now, we'll read it into memory/temp file.
    
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
    content = await file.read()
    
    if len(content) > 20 * 1024 * 1024: # 20MB
         raise HTTPException(
            status_code=400,
            detail={
                "detail": "File size exceeds 20 MB limit",
                "error_code": "FILE_SIZE_EXCEEDED",
                "max_size_mb": 20
            }
        )
        
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        # 4. Get or create File Search store for session
        store = get_or_create_file_search_store(session_id, user_id, db)

        # 5. Upload to Gemini File API
        result = gemini.upload_file_to_store(
            file_path=temp_path,
            store_name=store.gemini_store_name,
            display_name=file.filename,
            metadata={
                "session_id": session_id,
                "user_id": user_id,
                "original_filename": file.filename
            }
        )

        # 6. Store metadata in database
        uploaded_file = UploadedFile(
            session_id=session_id,
            user_id=user_id,
            file_name=file.filename,
            file_size=len(content),
            file_type=file.content_type,
            gemini_file_uri=result.file.uri,
            gemini_file_id=result.file.name.split("/")[-1],
            file_search_store_id=store.gemini_store_name
        )

        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)

        return uploaded_file

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

@router.get("/session/{session_id}", response_model=SessionFilesResponse)
async def list_session_files(
    session_id: str,
    db: Session = Depends(get_db)
):
    files = db.query(UploadedFile).filter_by(session_id=session_id).all()
    return {
        "session_id": session_id,
        "file_count": len(files),
        "files": files
    }
