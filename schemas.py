from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

# =============================================================================
# Legacy Models (kept for backward compatibility)
# =============================================================================

class MessageData(BaseModel):
    text: str
    store_name: Optional[str] = None
    file_count: Optional[int] = 0
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
    model_config = ConfigDict(protected_namespaces=())

    content: Dict[str, Any]
    grounding: GroundingMetadata
    generated_at: datetime
    model_used: str
    generation_method: str

# =============================================================================
# Shared Citation Models (v2.0)
# =============================================================================

class FileCitation(BaseModel):
    """Citation from an uploaded file"""
    source_type: str = "file"
    file_name: str
    file_uri: str
    page: Optional[int] = None
    section: Optional[str] = None
    content_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)

class WebCitation(BaseModel):
    """Citation from web search"""
    source_type: str = "web"
    url: str
    domain: str
    title: str
    published_date: Optional[str] = None
    content_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)

# =============================================================================
# File RAG - Overview (Director Agent use case)
# =============================================================================

class ContentTheme(BaseModel):
    """A theme/topic found in uploaded content"""
    theme_name: str
    description: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_files: List[str]
    key_points: List[str]

class DataPointSummary(BaseModel):
    """Summary of available data points in files"""
    category: str  # e.g., "Financial", "Customer", "Product"
    available_metrics: List[str]
    time_periods: Optional[List[str]] = None
    source_file: str

class DocumentStructure(BaseModel):
    """Structure summary of a document"""
    file_name: str
    document_type: str  # e.g., "report", "spreadsheet", "presentation"
    sections: List[str]
    page_count: Optional[int] = None
    has_tables: bool = False
    has_charts: bool = False

class FileRAGOverviewRequest(BaseModel):
    """Request for high-level file content overview"""
    store_name: str = Field(..., description="Gemini File Search store name")
    topic: str = Field(..., description="Topic or query for content overview")
    context: Optional[Dict[str, Any]] = Field(
        default={},
        description="Additional context (presentation_id, slide_context, etc.)"
    )
    max_themes: int = Field(default=5, ge=1, le=10, description="Max themes to identify")

class FileRAGOverviewResponse(BaseModel):
    """Response with high-level content overview"""
    model_config = ConfigDict(protected_namespaces=())

    success: bool
    themes: List[ContentTheme] = []
    data_points: List[DataPointSummary] = []
    document_structures: List[DocumentStructure] = []
    total_files_analyzed: int = 0
    relevance_summary: str = ""
    citations: List[FileCitation] = []
    generated_at: datetime
    model_used: str
    retrieval_mode: str = "file_overview"
    error: Optional[Dict[str, Any]] = None

# =============================================================================
# File RAG - Detailed (Text Service use case)
# =============================================================================

class ContentChunk(BaseModel):
    """A chunk of detailed content with source attribution"""
    content: str
    content_type: str  # "text", "data", "quote", "statistic"
    source_file: str
    source_uri: str
    page_reference: Optional[int] = None
    section_reference: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    relevance_to_query: float = Field(ge=0.0, le=1.0)

class FileRAGDetailedRequest(BaseModel):
    """Request for detailed file content with citations"""
    store_name: str = Field(..., description="Gemini File Search store name")
    query: str = Field(..., description="Specific query for slide content")
    context: Optional[Dict[str, Any]] = Field(
        default={},
        description="Slide context (type, position, presentation_title, etc.)"
    )
    max_chunks: int = Field(default=10, ge=1, le=20, description="Max content chunks")
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="Min confidence threshold")

class FileRAGDetailedResponse(BaseModel):
    """Response with detailed content chunks and citations"""
    model_config = ConfigDict(protected_namespaces=())

    success: bool
    content_chunks: List[ContentChunk] = []
    synthesized_content: str = ""
    citations: List[FileCitation] = []
    query_interpretation: str = ""
    total_chunks_found: int = 0
    chunks_returned: int = 0
    generated_at: datetime
    model_used: str
    retrieval_mode: str = "file_detailed"
    error: Optional[Dict[str, Any]] = None

# =============================================================================
# Web Search - Overview (Director Agent use case)
# =============================================================================

class WebSource(BaseModel):
    """A web source found during search"""
    title: str
    url: str
    domain: str
    source_type: str  # "news", "academic", "industry", "government", "blog"
    published_date: Optional[str] = None
    reliability_indicator: str  # "high", "medium", "low"
    key_insight: str

class WebTheme(BaseModel):
    """A theme identified from web research"""
    theme_name: str
    description: str
    perspective: str  # "mainstream", "emerging", "contrarian"
    supporting_sources: List[str]  # URLs

class WebSearchOverviewRequest(BaseModel):
    """Request for high-level web research overview"""
    topic: str = Field(..., description="Topic to research on the web")
    context: Optional[Dict[str, Any]] = Field(
        default={},
        description="Context for research focus"
    )
    industry_focus: Optional[str] = None
    recency_preference: str = Field(
        default="recent",
        description="Preference: recent, any, historical"
    )

class WebSearchOverviewResponse(BaseModel):
    """Response with web research overview"""
    model_config = ConfigDict(protected_namespaces=())

    success: bool
    summary: str = ""
    key_themes: List[WebTheme] = []
    top_sources: List[WebSource] = []
    suggested_angles: List[str] = []
    coverage_assessment: str = ""
    citations: List[WebCitation] = []
    search_results_found: int = 0
    results_analyzed: int = 0
    generated_at: datetime
    model_used: str
    retrieval_mode: str = "web_overview"
    error: Optional[Dict[str, Any]] = None

# =============================================================================
# Web Search - Detailed (Text Service use case)
# =============================================================================

class WebFact(BaseModel):
    """A specific fact from web search"""
    fact_type: str  # "statistic", "quote", "date", "definition", "claim"
    content: str
    source_url: str
    source_domain: str
    source_title: str
    published_date: Optional[str] = None
    verification_status: str  # "verified", "unverified", "conflicting"
    confidence_score: float = Field(ge=0.0, le=1.0)

class WebSearchDetailedRequest(BaseModel):
    """Request for detailed web facts with citations"""
    query: str = Field(..., description="Specific query for slide content")
    context: Optional[Dict[str, Any]] = Field(
        default={},
        description="Slide context"
    )
    data_types_needed: Optional[List[str]] = Field(
        default=["facts", "statistics", "quotes"],
        description="Types of data needed"
    )
    recency_required: bool = Field(
        default=True,
        description="Prioritize recent information"
    )

class WebSearchDetailedResponse(BaseModel):
    """Response with detailed web facts and citations"""
    model_config = ConfigDict(protected_namespaces=())

    success: bool
    facts: List[WebFact] = []
    synthesized_content: str = ""
    citations: List[WebCitation] = []
    data_recency: str = ""  # "current", "recent", "dated"
    source_diversity: str = ""  # "diverse", "limited", "single"
    search_results_found: int = 0
    facts_extracted: int = 0
    generated_at: datetime
    model_used: str
    retrieval_mode: str = "web_detailed"
    error: Optional[Dict[str, Any]] = None
