from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

class RAGConfig(BaseModel):
    store_name: Optional[str] = None

class ContentGenerationRequest(BaseModel):
    session_id: Optional[str] = None # Optional for logging
    user_id: Optional[str] = None # Optional for logging
    prompt: str
    slide_type: str
    context: Dict[str, Any] = {}
    rag_config: Optional[RAGConfig] = None

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
