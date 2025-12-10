from fastapi import APIRouter, HTTPException
from datetime import datetime
import json
import re

from schemas import (
    WebSearchOverviewRequest, WebSearchOverviewResponse,
    WebSearchDetailedRequest, WebSearchDetailedResponse,
    WebTheme, WebSource, WebFact, WebCitation
)
from services import gemini

router = APIRouter(
    prefix="/api/v1/search/web",
    tags=["web-search"]
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


@router.post("/overview", response_model=WebSearchOverviewResponse)
async def web_search_overview(request: WebSearchOverviewRequest):
    """
    Get high-level web research overview.

    **Use case:** Director Agent researching topic for presentation planning

    Returns:
    - Summary of key web findings
    - Main themes identified from diverse sources
    - Top 3-5 most reliable sources with insights
    - Suggested angles for presentation
    - Assessment of online coverage quality

    **Note:** This endpoint does NOT fall back to standard LLM if web search fails.
    Errors are returned directly to allow the caller to handle appropriately.
    """
    try:
        response = gemini.generate_web_search_overview(
            topic=request.topic,
            context=request.context or {},
            industry_focus=request.industry_focus,
            recency_preference=request.recency_preference
        )

        # Parse the LLM response
        parsed = parse_json_response(response.text)

        # Extract citations from grounding metadata
        raw_citations = gemini.extract_web_citations(response)

        # Convert raw citations to WebCitation objects
        citations = [
            WebCitation(
                source_type="web",
                url=c.get("url", ""),
                domain=c.get("domain", ""),
                title=c.get("title", "Unknown"),
                published_date=c.get("published_date"),
                content_snippet=c.get("content_snippet", ""),
                confidence=c.get("confidence", 0.8)
            )
            for c in raw_citations
        ]

        # Parse key themes from response
        key_themes = []
        for t in safe_get(parsed, "key_themes", []):
            try:
                key_themes.append(WebTheme(
                    theme_name=t.get("theme_name", "Unknown"),
                    description=t.get("description", ""),
                    perspective=t.get("perspective", "mainstream"),
                    supporting_sources=t.get("supporting_sources", [])
                ))
            except Exception:
                continue

        # Parse top sources from response
        top_sources = []
        for s in safe_get(parsed, "top_sources", []):
            try:
                url = s.get("url", "")
                domain = s.get("domain", "")
                if not domain and url and "//" in url:
                    try:
                        domain = url.split("//")[1].split("/")[0]
                    except:
                        domain = ""

                top_sources.append(WebSource(
                    title=s.get("title", "Unknown"),
                    url=url,
                    domain=domain,
                    source_type=s.get("source_type", "unknown"),
                    published_date=s.get("published_date"),
                    reliability_indicator=s.get("reliability_indicator", "medium"),
                    key_insight=s.get("key_insight", "")
                ))
            except Exception:
                continue

        return WebSearchOverviewResponse(
            success=True,
            summary=safe_get(parsed, "summary", ""),
            key_themes=key_themes,
            top_sources=top_sources,
            suggested_angles=safe_get(parsed, "suggested_angles", []),
            coverage_assessment=safe_get(parsed, "coverage_assessment", ""),
            citations=citations,
            search_results_found=10,  # Gemini typically fetches ~10 results
            results_analyzed=len(citations) if citations else len(top_sources),
            generated_at=datetime.utcnow(),
            model_used="gemini-2.0-flash"
        )

    except Exception as e:
        # NO FALLBACK - web search failure is an error
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "WEB_SEARCH_OVERVIEW_FAILED",
                "message": str(e),
                "suggestion": "Web search unavailable. Consider using file-based RAG if you have uploaded documents."
            }
        )


@router.post("/detailed", response_model=WebSearchDetailedResponse)
async def web_search_detailed(request: WebSearchDetailedRequest):
    """
    Get detailed web facts with citations.

    **Use case:** Text Service needing specific facts from web for slide content

    Returns:
    - Specific facts, statistics, quotes from web
    - Each fact with source URL, verification status, confidence
    - Synthesized content ready for slide use
    - Assessment of data recency and source diversity

    **Note:** This endpoint does NOT fall back to standard LLM if web search fails.
    Errors are returned directly to allow the caller to handle appropriately.
    """
    try:
        response = gemini.generate_web_search_detailed(
            query=request.query,
            context=request.context or {},
            data_types_needed=request.data_types_needed or ["facts", "statistics", "quotes"],
            recency_required=request.recency_required
        )

        # Parse the LLM response
        parsed = parse_json_response(response.text)

        # Extract citations from grounding metadata
        raw_citations = gemini.extract_web_citations(response)

        # Convert raw citations to WebCitation objects
        citations = [
            WebCitation(
                source_type="web",
                url=c.get("url", ""),
                domain=c.get("domain", ""),
                title=c.get("title", "Unknown"),
                published_date=c.get("published_date"),
                content_snippet=c.get("content_snippet", ""),
                confidence=c.get("confidence", 0.8)
            )
            for c in raw_citations
        ]

        # Parse facts from response
        facts = []
        for f in safe_get(parsed, "facts", []):
            try:
                source_url = f.get("source_url", "")
                source_domain = f.get("source_domain", "")
                if not source_domain and source_url and "//" in source_url:
                    try:
                        source_domain = source_url.split("//")[1].split("/")[0]
                    except:
                        source_domain = ""

                facts.append(WebFact(
                    fact_type=f.get("fact_type", "claim"),
                    content=f.get("content", ""),
                    source_url=source_url,
                    source_domain=source_domain,
                    source_title=f.get("source_title", "Unknown"),
                    published_date=f.get("published_date"),
                    verification_status=f.get("verification_status", "unverified"),
                    confidence_score=float(f.get("confidence_score", 0.7))
                ))
            except Exception:
                continue

        return WebSearchDetailedResponse(
            success=True,
            facts=facts,
            synthesized_content=safe_get(parsed, "synthesized_content", ""),
            citations=citations,
            data_recency=safe_get(parsed, "data_recency", "recent"),
            source_diversity=safe_get(parsed, "source_diversity", "diverse"),
            search_results_found=10,
            facts_extracted=len(facts),
            generated_at=datetime.utcnow(),
            model_used="gemini-2.0-flash"
        )

    except Exception as e:
        # NO FALLBACK - web search failure is an error
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "WEB_SEARCH_DETAILED_FAILED",
                "message": str(e),
                "suggestion": "Web search unavailable. Consider using file-based RAG if you have uploaded documents."
            }
        )
