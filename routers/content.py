from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import json
import re

from ..database import get_db
from ..models import UploadedFile, FileSearchStore
from ..schemas import ContentGenerationRequest, ContentGenerationResponse
from ..services import gemini

router = APIRouter(
    prefix="/api/v1/content",
    tags=["content"]
)

def parse_slide_content(text: str, slide_type: str):
    # Basic parsing logic - in a real app this would be more robust or use structured output
    # For now, we'll try to extract JSON if present, or return text structure
    try:
        # Find JSON block
        match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return {"raw_text": text}
    except:
        return {"raw_text": text}

def extract_citations(response, files):
    citations = []
    if not response.candidates:
        return citations
        
    candidate = response.candidates[0]
    if not hasattr(candidate, 'grounding_metadata') or not candidate.grounding_metadata:
        return citations
        
    grounding_metadata = candidate.grounding_metadata
    
    # Map chunks to files
    # Note: Gemini 2.0 Flash grounding metadata structure might differ slightly from 1.5
    # We will implement a best-effort mapping based on available fields
    
    if hasattr(grounding_metadata, 'grounding_chunks'):
        for chunk in grounding_metadata.grounding_chunks:
            # This is a simplification. Real mapping requires matching indices.
            # For now, we'll just return the content.
            citations.append({
                "file_name": "Unknown", # improved mapping needed
                "file_uri": "Unknown",
                "chunks": [{
                    "content": chunk.web.title if hasattr(chunk, 'web') and chunk.web else "Content from file",
                    "confidence": 0.9 # Placeholder
                }]
            })
            
    return citations

@router.post("/generate", response_model=ContentGenerationResponse)
async def generate_content(
    request: ContentGenerationRequest,
    db: Session = Depends(get_db)
):
    # 1. Check if files exist for session
    files = db.query(UploadedFile).filter_by(session_id=request.session_id).all()

    if files and len(files) > 0:
        # RAG-based generation
        try:
            # Get File Search store for session
            store = db.query(FileSearchStore).filter_by(session_id=request.session_id).first()

            if not store:
                # Should not happen if files exist, but handle gracefully
                raise ValueError("Store not found")

            # Generate content with File Search
            response = gemini.generate_content_with_rag(
                prompt=request.prompt,
                context=request.context,
                store_name=store.gemini_store_name
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
                "generated_at": datetime.utcnow(),
                "model_used": "gemini-2.0-flash",
                "generation_method": "rag"
            }

        except Exception as e:
            # Fallback to standard generation on error
            print(f"RAG generation failed: {e}. Falling back to standard LLM.")
            pass

    # Fallback: Standard LLM generation (no files)
    try:
        response = gemini.generate_content_standard(
            prompt=request.prompt,
            context=request.context
        )

        content = parse_slide_content(response.text, request.slide_type)

        return {
            "content": content,
            "grounding": {
                "used_files": False,
                "file_count": 0,
                "citations": []
            },
            "generated_at": datetime.utcnow(),
            "model_used": "gemini-2.0-flash",
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
