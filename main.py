from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from routers import content, file_rag, web_search

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Deckster RAG & Search Service",
    description="""
Multi-mode content retrieval service for Deckster presentation builder using Google Gemini.

## Features

### File RAG (Retrieval-Augmented Generation)
- **Overview Endpoint**: High-level content analysis for Director Agent straw man planning
- **Detailed Endpoint**: Specific content extraction with citations for Text Service slide building

### Web Search
- **Overview Endpoint**: Web research summary for topic planning
- **Detailed Endpoint**: Specific facts and statistics from web sources

## Authentication
Uses Google Cloud Application Default Credentials for Vertex AI access.

## Version
2.0.0
    """,
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(content.router)       # Legacy endpoint (backward compatibility)
app.include_router(file_rag.router)      # File RAG endpoints (v2.0)
app.include_router(web_search.router)    # Web Search endpoints (v2.0)


@app.get("/")
async def root():
    """Service information and available endpoints"""
    return {
        "service": "Deckster RAG & Search Service",
        "version": "2.0.0",
        "status": "ok",
        "endpoints": {
            "file_rag": {
                "overview": {
                    "path": "/api/v1/rag/file/overview",
                    "method": "POST",
                    "description": "High-level content overview for Director Agent"
                },
                "detailed": {
                    "path": "/api/v1/rag/file/detailed",
                    "method": "POST",
                    "description": "Detailed content with citations for Text Service"
                }
            },
            "web_search": {
                "overview": {
                    "path": "/api/v1/search/web/overview",
                    "method": "POST",
                    "description": "Web research overview for Director Agent"
                },
                "detailed": {
                    "path": "/api/v1/search/web/detailed",
                    "method": "POST",
                    "description": "Detailed web facts for Text Service"
                }
            },
            "legacy": {
                "generate": {
                    "path": "/api/v1/content/generate",
                    "method": "POST",
                    "description": "Legacy content generation (backward compatible)"
                }
            }
        },
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": "2.0.0",
        "service": "rag-search-service"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
