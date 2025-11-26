from fastapi import APIRouter, HTTPException
from datetime import datetime
import json
import re

from ..schemas import ContentGenerationRequest, ContentGenerationResponse
from ..services import gemini

router = APIRouter(
    prefix="/api/v1/content",
    tags=["content"]
)

def parse_slide_content(text: str, slide_type: str):
    try:
        match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return {"raw_text": text}
    except:
        return {"raw_text": text}

def extract_citations(response):
    citations = []
    if not response.candidates:
        return citations
        
    candidate = response.candidates[0]
    if not hasattr(candidate, 'grounding_metadata') or not candidate.grounding_metadata:
        return citations
        
    grounding_metadata = candidate.grounding_metadata
    
    if hasattr(grounding_metadata, 'grounding_chunks'):
        for chunk in grounding_metadata.grounding_chunks:
            citations.append({
                "file_name": "Unknown", 
                "file_uri": "Unknown",
                "chunks": [{
                    "content": chunk.web.title if hasattr(chunk, 'web') and chunk.web else "Content from file",
                    "confidence": 0.9 
                }]
            })
            
    return citations

@router.post("/generate", response_model=ContentGenerationResponse)
async def generate_content(request: ContentGenerationRequest):
    # Check if store_name is provided for RAG
    if request.rag_config and request.rag_config.store_name:
        try:
            # Generate content with File Search
            response = gemini.generate_content_with_rag(
                prompt=request.prompt,
                context=request.context,
                store_name=request.rag_config.store_name
            )

            content = parse_slide_content(response.text, request.slide_type)
            citations = extract_citations(response)

            return {
                "content": content,
                "grounding": {
                    "used_files": True,
                    "file_count": 0, # We don't know the count without querying the store, which is fine
                    "citations": citations
                },
                "generated_at": datetime.utcnow(),
                "model_used": "gemini-2.0-flash",
                "generation_method": "rag"
            }

        except Exception as e:
            print(f"RAG generation failed: {e}. Falling back to standard LLM.")
            pass

    # Fallback or Standard LLM generation
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
