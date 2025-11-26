from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any

class MessageData(BaseModel):
    text: str
    store_name: Optional[str] = None
    file_count: Optional[int] = 0
    # Keeping these as optional in case they are still sent or needed for the logic
    slide_type: Optional[str] = "text" 
    context: Optional[Dict[str, Any]] = {}

class ContentGenerationRequest(BaseModel):
    type: str
    data: MessageData

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
