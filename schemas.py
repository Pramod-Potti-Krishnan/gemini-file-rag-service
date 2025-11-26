from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

class UploadedFileBase(BaseModel):
    session_id: str
    user_id: str
    file_name: str
    file_size: int
    file_type: str
    gemini_file_uri: str
    gemini_file_id: str
    file_search_store_id: str

class UploadedFileCreate(UploadedFileBase):
    pass

class UploadedFileResponse(UploadedFileBase):
    id: int
    uploaded_at: datetime
    status: str = "indexed"

    class Config:
        from_attributes = True

class SessionFilesResponse(BaseModel):
    session_id: str
    file_count: int
    files: List[UploadedFileResponse]

class ContentGenerationRequest(BaseModel):
    session_id: str
    user_id: str
    prompt: str
    slide_type: str
    context: Dict[str, Any] = {}

class CitationChunk(BaseModel):
    content: str
    page: Optional[int] = None
    confidence: Optional[float] = None

class Citation(BaseModel):
    file_name: str
    file_uri: str
    chunks: List[CitationChunk]

class GroundingMetadata(BaseModel):
    used_files: bool
    file_count: int
    citations: List[Citation]

class ContentGenerationResponse(BaseModel):
    content: Dict[str, Any]
    grounding: GroundingMetadata
    generated_at: datetime
    model_used: str
    generation_method: str
