from fastapi import APIRouter, HTTPException
from datetime import datetime
import json
import re

from schemas import (
    FileRAGOverviewRequest, FileRAGOverviewResponse,
    FileRAGDetailedRequest, FileRAGDetailedResponse,
    ContentTheme, DataPointSummary, DocumentStructure,
    ContentChunk, FileCitation
)
from services import gemini

router = APIRouter(
    prefix="/api/v1/rag/file",
    tags=["file-rag"]
)


def parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks"""
    try:
        # Try to find JSON in markdown code block
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Try parsing entire response as JSON
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_text": text}


def safe_get(data: dict, key: str, default=None):
    """Safely get a value from a dict"""
    return data.get(key, default) if isinstance(data, dict) else default


@router.post("/overview", response_model=FileRAGOverviewResponse)
async def file_rag_overview(request: FileRAGOverviewRequest):
    """
    Get high-level overview of uploaded file content.

    **Use case:** Director Agent preparing straw man presentation outline

    Returns:
    - Main themes/topics found in uploaded files
    - Available data points and metrics
    - Document structure summaries
    - Relevance assessment for the specified topic
    - Citations linking content to source files
    """
    try:
        response = gemini.generate_file_rag_overview(
            store_name=request.store_name,
            topic=request.topic,
            context=request.context or {},
            max_themes=request.max_themes
        )

        # Parse the LLM response
        parsed = parse_json_response(response.text)

        # Extract citations from grounding metadata
        raw_citations = gemini.extract_file_citations(response, request.store_name)

        # Convert raw citations to FileCitation objects
        citations = [
            FileCitation(
                source_type="file",
                file_name=c.get("file_name", "Unknown"),
                file_uri=c.get("file_uri", request.store_name),
                page=c.get("page"),
                section=c.get("section"),
                content_snippet=c.get("content_snippet", ""),
                confidence=c.get("confidence", 0.9)
            )
            for c in raw_citations
        ]

        # Parse themes from response
        themes = []
        for t in safe_get(parsed, "themes", []):
            try:
                themes.append(ContentTheme(
                    theme_name=t.get("theme_name", "Unknown"),
                    description=t.get("description", ""),
                    relevance_score=float(t.get("relevance_score", 0.8)),
                    source_files=t.get("source_files", []),
                    key_points=t.get("key_points", [])
                ))
            except Exception:
                continue

        # Parse data points from response
        data_points = []
        for dp in safe_get(parsed, "data_points", []):
            try:
                data_points.append(DataPointSummary(
                    category=dp.get("category", "General"),
                    available_metrics=dp.get("available_metrics", []),
                    time_periods=dp.get("time_periods"),
                    source_file=dp.get("source_file", "Unknown")
                ))
            except Exception:
                continue

        # Parse document structures from response
        doc_structures = []
        for ds in safe_get(parsed, "document_structures", []):
            try:
                doc_structures.append(DocumentStructure(
                    file_name=ds.get("file_name", "Unknown"),
                    document_type=ds.get("document_type", "document"),
                    sections=ds.get("sections", []),
                    page_count=ds.get("page_count"),
                    has_tables=ds.get("has_tables", False),
                    has_charts=ds.get("has_charts", False)
                ))
            except Exception:
                continue

        return FileRAGOverviewResponse(
            success=True,
            themes=themes,
            data_points=data_points,
            document_structures=doc_structures,
            total_files_analyzed=len(citations) if citations else len(doc_structures),
            relevance_summary=safe_get(parsed, "relevance_summary", ""),
            citations=citations,
            generated_at=datetime.utcnow(),
            model_used="gemini-2.0-flash"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "FILE_RAG_OVERVIEW_FAILED",
                "message": str(e)
            }
        )


@router.post("/detailed", response_model=FileRAGDetailedResponse)
async def file_rag_detailed(request: FileRAGDetailedRequest):
    """
    Get detailed content chunks with citations.

    **Use case:** Text Service building specific slide content

    Returns:
    - Specific content chunks matching the query
    - Each chunk with source file, page reference, and confidence
    - Synthesized content ready for slide use
    - Full citations for attribution
    """
    try:
        response = gemini.generate_file_rag_detailed(
            store_name=request.store_name,
            query=request.query,
            context=request.context or {},
            max_chunks=request.max_chunks,
            min_confidence=request.min_confidence
        )

        # Parse the LLM response
        parsed = parse_json_response(response.text)

        # Extract citations from grounding metadata
        raw_citations = gemini.extract_file_citations(response, request.store_name)

        # Convert raw citations to FileCitation objects
        citations = [
            FileCitation(
                source_type="file",
                file_name=c.get("file_name", "Unknown"),
                file_uri=c.get("file_uri", request.store_name),
                page=c.get("page"),
                section=c.get("section"),
                content_snippet=c.get("content_snippet", ""),
                confidence=c.get("confidence", 0.9)
            )
            for c in raw_citations
        ]

        # Parse content chunks from response
        content_chunks = []
        for chunk in safe_get(parsed, "content_chunks", []):
            try:
                content_chunks.append(ContentChunk(
                    content=chunk.get("content", ""),
                    content_type=chunk.get("content_type", "text"),
                    source_file=chunk.get("source_file", "Unknown"),
                    source_uri=chunk.get("source_uri", request.store_name),
                    page_reference=chunk.get("page_reference"),
                    section_reference=chunk.get("section_reference"),
                    confidence_score=float(chunk.get("confidence_score", 0.8)),
                    relevance_to_query=float(chunk.get("relevance_to_query", 0.8))
                ))
            except Exception:
                continue

        return FileRAGDetailedResponse(
            success=True,
            content_chunks=content_chunks,
            synthesized_content=safe_get(parsed, "synthesized_content", ""),
            citations=citations,
            query_interpretation=safe_get(parsed, "query_interpretation", ""),
            total_chunks_found=len(content_chunks),
            chunks_returned=min(len(content_chunks), request.max_chunks),
            generated_at=datetime.utcnow(),
            model_used="gemini-2.0-flash"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "FILE_RAG_DETAILED_FAILED",
                "message": str(e)
            }
        )
