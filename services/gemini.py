import os
import json
from google import genai
from google.genai import types
from datetime import datetime
from typing import Dict, List, Optional, Any

# =============================================================================
# Client Management
# =============================================================================

def get_gemini_client():
    """Creates Vertex AI client with Application Default Credentials"""
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")

    if not project or not location:
        raise ValueError("GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION environment variables must be set")

    return genai.Client(
        vertexai=True,
        project=project,
        location=location
    )

# =============================================================================
# Legacy Functions (kept for backward compatibility)
# =============================================================================

def create_file_search_store(session_id: str, user_id: str):
    """Create a File Search store for a session"""
    client = get_gemini_client()
    store = client.file_search_stores.create(
        display_name=f"Session_{session_id}",
        metadata={
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat()
        }
    )
    return store

def upload_file_to_store(file_path: str, store_name: str, display_name: str, metadata: dict):
    """Upload file directly to File Search store"""
    client = get_gemini_client()

    operation = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store_name,
        display_name=display_name,
        metadata=metadata
    )

    result = operation.result()
    return result

def generate_content_with_rag(prompt: str, context: dict, store_name: str):
    """Legacy RAG generation - kept for backward compatibility"""
    client = get_gemini_client()

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"{prompt}\n\nContext: {context}",
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearchTool(
                        file_search_store_names=[store_name]
                    )
                )
            ],
            temperature=0.7,
            max_output_tokens=2048
        )
    )
    return response

def generate_content_standard(prompt: str, context: dict):
    """Standard LLM generation without grounding"""
    client = get_gemini_client()

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"{prompt}\n\nContext: {context}",
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=2048
        )
    )
    return response

# =============================================================================
# File RAG Functions (v2.0)
# =============================================================================

def generate_file_rag_overview(
    store_name: str,
    topic: str,
    context: Dict[str, Any],
    max_themes: int = 5
) -> Any:
    """
    Generate high-level overview of file content for Director Agent.

    Returns themes, data points, and document structures with citations.
    """
    client = get_gemini_client()

    context_str = json.dumps(context) if context else "{}"

    overview_prompt = f"""Analyze the uploaded documents and provide a high-level overview for the topic: "{topic}"

Context: {context_str}

Please identify and return a JSON response with the following structure:
{{
    "themes": [
        {{
            "theme_name": "string",
            "description": "string",
            "relevance_score": 0.0-1.0,
            "source_files": ["file1.pdf", "file2.docx"],
            "key_points": ["point1", "point2", "point3"]
        }}
    ],
    "data_points": [
        {{
            "category": "Financial|Customer|Product|etc",
            "available_metrics": ["metric1", "metric2"],
            "time_periods": ["Q1 2024", "Q2 2024"],
            "source_file": "filename.xlsx"
        }}
    ],
    "document_structures": [
        {{
            "file_name": "string",
            "document_type": "report|spreadsheet|presentation",
            "sections": ["section1", "section2"],
            "page_count": null,
            "has_tables": true/false,
            "has_charts": true/false
        }}
    ],
    "relevance_summary": "A 2-3 sentence summary of how relevant the uploaded content is to the specified topic"
}}

Important:
- Identify up to {max_themes} main themes
- Focus on content that would be useful for building a presentation
- Include all available data points and metrics
- Be specific about which files contain what information"""

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=overview_prompt,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearchTool(
                        file_search_store_names=[store_name]
                    )
                )
            ],
            temperature=0.5,
            max_output_tokens=4096
        )
    )

    return response


def generate_file_rag_detailed(
    store_name: str,
    query: str,
    context: Dict[str, Any],
    max_chunks: int = 10,
    min_confidence: float = 0.7
) -> Any:
    """
    Generate detailed content with citations for Text Service.

    Returns specific content chunks with page references and confidence scores.
    """
    client = get_gemini_client()

    context_str = json.dumps(context) if context else "{}"

    detailed_prompt = f"""Find specific content from the uploaded documents for the following query:

Query: "{query}"
Context: {context_str}

Please return a JSON response with the following structure:
{{
    "content_chunks": [
        {{
            "content": "Exact text or data from the document",
            "content_type": "text|data|quote|statistic",
            "source_file": "filename.pdf",
            "source_uri": "file URI if available",
            "page_reference": 3,
            "section_reference": "Section name if available",
            "confidence_score": 0.0-1.0,
            "relevance_to_query": 0.0-1.0
        }}
    ],
    "synthesized_content": "A coherent paragraph synthesizing the key information from the chunks that directly answers the query",
    "query_interpretation": "Brief description of how you understood and approached the query"
}}

Important:
- Extract up to {max_chunks} most relevant content chunks
- Only include chunks with confidence >= {min_confidence}
- For each chunk, provide exact page or section references when available
- The synthesized_content should be suitable for direct use in a presentation slide
- Prioritize factual, specific information over general statements"""

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=detailed_prompt,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearchTool(
                        file_search_store_names=[store_name]
                    )
                )
            ],
            temperature=0.3,
            max_output_tokens=4096
        )
    )

    return response


# =============================================================================
# Web Search Functions (v2.0)
# =============================================================================

def generate_web_search_overview(
    topic: str,
    context: Dict[str, Any],
    industry_focus: Optional[str] = None,
    recency_preference: str = "recent"
) -> Any:
    """
    Generate high-level web research overview for Director Agent.

    Uses GoogleSearchRetrieval to search web and identify themes, sources, and angles.
    """
    client = get_gemini_client()

    context_str = json.dumps(context) if context else "{}"
    industry_clause = f"Focus on {industry_focus} industry perspective." if industry_focus else ""
    recency_clause = "Prioritize recent information from the last 1-2 years." if recency_preference == "recent" else ""

    overview_prompt = f"""Research the following topic on the web and provide a high-level overview:

Topic: "{topic}"
Context: {context_str}
{industry_clause}
{recency_clause}

Please return a JSON response with the following structure:
{{
    "summary": "A 2-3 paragraph summary of key findings from web research",
    "key_themes": [
        {{
            "theme_name": "string",
            "description": "string",
            "perspective": "mainstream|emerging|contrarian",
            "supporting_sources": ["url1", "url2"]
        }}
    ],
    "top_sources": [
        {{
            "title": "Article or page title",
            "url": "https://...",
            "domain": "example.com",
            "source_type": "news|academic|industry|government|blog",
            "published_date": "2024-01-15 or null",
            "reliability_indicator": "high|medium|low",
            "key_insight": "What this source uniquely contributes"
        }}
    ],
    "suggested_angles": [
        "Angle 1: Description of perspective to consider",
        "Angle 2: Another perspective"
    ],
    "coverage_assessment": "Brief assessment of how well this topic is covered online and quality of available sources"
}}

Important:
- Identify 3-5 main themes from diverse sources
- Include only the 3-5 most reliable and relevant sources
- Assess source reliability (prefer news, academic, government, industry over blogs)
- Suggest different angles that could be taken in a presentation
- Be specific about what each source contributes"""

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=overview_prompt,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search_retrieval=types.GoogleSearchRetrieval(
                        dynamic_retrieval_config=types.DynamicRetrievalConfig(
                            mode=types.DynamicRetrievalConfigMode.MODE_DYNAMIC,
                            dynamic_threshold=0.6,
                        )
                    )
                )
            ],
            temperature=0.5,
            max_output_tokens=4096
        )
    )

    return response


def generate_web_search_detailed(
    query: str,
    context: Dict[str, Any],
    data_types_needed: List[str] = None,
    recency_required: bool = True
) -> Any:
    """
    Generate detailed web facts with citations for Text Service.

    Uses GoogleSearchRetrieval to find specific facts, statistics, and quotes.
    """
    client = get_gemini_client()

    if data_types_needed is None:
        data_types_needed = ["facts", "statistics", "quotes"]

    context_str = json.dumps(context) if context else "{}"
    data_types_str = ", ".join(data_types_needed)
    recency_clause = "Prioritize the most recent information available (last 1-2 years)." if recency_required else ""

    detailed_prompt = f"""Find specific, factual information from the web for:

Query: "{query}"
Context: {context_str}
Data types needed: {data_types_str}
{recency_clause}

Please return a JSON response with the following structure:
{{
    "facts": [
        {{
            "fact_type": "statistic|quote|date|definition|claim",
            "content": "The exact fact, statistic, or quote",
            "source_url": "https://...",
            "source_domain": "example.com",
            "source_title": "Article title",
            "published_date": "2024-01-15 or null",
            "verification_status": "verified|unverified|conflicting",
            "confidence_score": 0.0-1.0
        }}
    ],
    "synthesized_content": "A coherent paragraph synthesizing the facts, suitable for direct use in a presentation slide",
    "data_recency": "current|recent|dated",
    "source_diversity": "diverse|limited|single"
}}

Important:
- Extract 5-8 most relevant and verifiable facts
- Mark facts as "verified" only if found in multiple authoritative sources
- Include exact statistics and numbers when available
- Prioritize authoritative sources (government, academic, major news)
- The synthesized_content should be suitable for a presentation slide
- Be specific about dates and sources for each fact"""

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=detailed_prompt,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search_retrieval=types.GoogleSearchRetrieval(
                        dynamic_retrieval_config=types.DynamicRetrievalConfig(
                            mode=types.DynamicRetrievalConfigMode.MODE_DYNAMIC,
                            dynamic_threshold=0.8,
                        )
                    )
                )
            ],
            temperature=0.2,
            max_output_tokens=4096
        )
    )

    return response


# =============================================================================
# Citation Extraction Utilities (v2.0)
# =============================================================================

def extract_file_citations(response: Any, store_name: str) -> List[Dict]:
    """
    Extract file citations from Gemini response grounding metadata.

    Returns list of citation dictionaries with file info and content snippets.
    """
    citations = []

    if not response.candidates:
        return citations

    candidate = response.candidates[0]
    if not hasattr(candidate, 'grounding_metadata') or not candidate.grounding_metadata:
        return citations

    grounding_metadata = candidate.grounding_metadata

    if hasattr(grounding_metadata, 'grounding_chunks'):
        for chunk in grounding_metadata.grounding_chunks:
            if hasattr(chunk, 'retrieved_context'):
                ctx = chunk.retrieved_context
                citations.append({
                    "source_type": "file",
                    "file_name": getattr(ctx, 'title', 'Unknown'),
                    "file_uri": getattr(ctx, 'uri', store_name),
                    "page": None,
                    "section": None,
                    "content_snippet": getattr(ctx, 'text', '')[:500],
                    "confidence": getattr(chunk, 'confidence_score', 0.9)
                })

    return citations


def extract_web_citations(response: Any) -> List[Dict]:
    """
    Extract web citations from Gemini response grounding metadata.

    Returns list of citation dictionaries with URLs and content snippets.
    """
    citations = []

    if not response.candidates:
        return citations

    candidate = response.candidates[0]
    if not hasattr(candidate, 'grounding_metadata') or not candidate.grounding_metadata:
        return citations

    grounding_metadata = candidate.grounding_metadata

    if hasattr(grounding_metadata, 'grounding_chunks'):
        for chunk in grounding_metadata.grounding_chunks:
            if hasattr(chunk, 'web'):
                web = chunk.web
                url = getattr(web, 'uri', '')

                # Extract domain from URL
                domain = ''
                if url and '//' in url:
                    try:
                        domain = url.split('//')[1].split('/')[0]
                    except:
                        domain = ''

                citations.append({
                    "source_type": "web",
                    "url": url,
                    "domain": domain,
                    "title": getattr(web, 'title', 'Unknown'),
                    "published_date": None,
                    "content_snippet": getattr(chunk, 'content', '')[:500] if hasattr(chunk, 'content') else '',
                    "confidence": getattr(chunk, 'confidence_score', 0.8)
                })

    # Also check for grounding_supports if grounding_chunks is not available
    if not citations and hasattr(grounding_metadata, 'grounding_supports'):
        for support in grounding_metadata.grounding_supports:
            if hasattr(support, 'grounding_chunk_indices'):
                # This is an alternate structure some responses use
                pass

    # Check for search_entry_point which may contain web results
    if hasattr(grounding_metadata, 'search_entry_point'):
        sep = grounding_metadata.search_entry_point
        if hasattr(sep, 'rendered_content'):
            # Contains rendered HTML of search results - could parse if needed
            pass

    return citations
