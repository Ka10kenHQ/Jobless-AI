from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Annotated
from pydantic import BaseModel, Field, BeforeValidator
from bson import ObjectId
from enum import Enum


def validate_object_id(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str):
        if ObjectId.is_valid(v):
            return ObjectId(v)
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[ObjectId, BeforeValidator(validate_object_id)]


class JobPosting(BaseModel):
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    url: str = Field(..., description="Unique job posting URL")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location")
    description: Optional[str] = Field(None, description="Job description")
    salary: Optional[str] = Field(None, description="Salary information")
    requirements: Optional[List[str]] = Field(default_factory=list, description="Job requirements")
    skills: Optional[List[str]] = Field(default_factory=list, description="Required skills")
    experience_level: Optional[str] = Field(None, description="Experience level required")
    job_type: Optional[str] = Field(None, description="Job type (full-time, part-time, etc.)")
    remote: Optional[bool] = Field(None, description="Remote work availability")
    
    # Metadata
    source: str = Field(..., description="Data source (LinkedIn, Indeed, etc.)")
    language: str = Field(default="english", description="Content language")
    country: Optional[str] = Field(None, description="Country")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(None)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Analysis
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="Data quality score")
    match_keywords: Optional[List[str]] = Field(default_factory=list)
    
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class TrainingExample(BaseModel):
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    example_id: str = Field(..., description="Unique example identifier")
    
    # Training data
    input_text: str = Field(..., description="Input text for training")
    output_text: str = Field(..., description="Expected output text")
    prompt_template: Optional[str] = Field(None, description="Prompt template used")
    
    # Metadata
    source: str = Field(..., description="Data source (synthetic, real, etc.)")
    language: str = Field(default="english", description="Content language")
    task_type: str = Field(..., description="Training task type")
    
    # Related job posting
    job_id: Optional[PyObjectId] = Field(None, description="Related job posting ID")
    
    # Quality metrics
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    validation_score: Optional[float] = Field(None, ge=0, le=1)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class UserInteraction(BaseModel):
    """User interaction model for chat logs"""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # User information
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    
    # Interaction data
    message: str = Field(..., description="User message")
    response: Optional[str] = Field(None, description="AI response")
    message_type: str = Field(default="query", description="Message type")
    
    # Extracted information
    extracted_requirements: Optional[Dict[str, Any]] = Field(None)
    matched_jobs: Optional[List[PyObjectId]] = Field(default_factory=list)
    search_results_count: Optional[int] = Field(None)
    
    # Context
    language: str = Field(default="english", description="Message language")
    user_agent: Optional[str] = Field(None)
    ip_address: Optional[str] = Field(None)
    
    # Performance metrics
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    satisfaction_score: Optional[float] = Field(None, ge=0, le=1)
    
    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ModelInfo(BaseModel):
    """Model training and metadata information"""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # Model identification
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    base_model: str = Field(..., description="Base model used")
    
    # Training configuration
    languages: List[str] = Field(..., description="Supported languages")
    training_config: Dict[str, Any] = Field(..., description="Training configuration")
    gpu_used: Optional[str] = Field(None, description="GPU used for training")
    
    # Training metrics
    training_loss: Optional[float] = Field(None)
    validation_loss: Optional[float] = Field(None)
    training_samples: Optional[int] = Field(None)
    training_time_minutes: Optional[float] = Field(None)
    
    # Model files
    model_file_path: str = Field(..., description="Path to model files")
    tokenizer_path: Optional[str] = Field(None)
    config_path: Optional[str] = Field(None)
    
    # Performance metrics
    avg_response_time_ms: Optional[float] = Field(None)
    accuracy_score: Optional[float] = Field(None, ge=0, le=1)
    
    # Status
    status: str = Field(default="training", description="Model status")
    is_active: bool = Field(default=False, description="Is currently active model")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    training_started_at: Optional[datetime] = Field(None)
    training_completed_at: Optional[datetime] = Field(None)
    
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True, "protected_namespaces": ()}


class ScrapingSession(BaseModel):
    """Scraping session tracking"""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # Session info
    source: str = Field(..., description="Scraping source")
    keywords: List[str] = Field(..., description="Search keywords")
    location: Optional[str] = Field(None, description="Search location")
    
    # Results
    jobs_found: int = Field(default=0, description="Number of jobs found")
    jobs_saved: int = Field(default=0, description="Number of jobs saved")
    duplicates_skipped: int = Field(default=0, description="Duplicates skipped")
    errors_count: int = Field(default=0, description="Number of errors")
    
    # Status
    status: str = Field(default="running", description="Session status")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    
    # Performance
    duration_seconds: Optional[float] = Field(None, description="Session duration")
    pages_scraped: Optional[int] = Field(None, description="Number of pages scraped")
    rate_limit_hits: Optional[int] = Field(None, description="Rate limit hits")
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ChatMessage(BaseModel):
    """Individual chat message model"""
    
    message_id: str = Field(..., description="Unique message identifier")
    content: str = Field(..., description="Message content")
    sender: str = Field(..., description="Message sender (user/bot)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional data for bot messages
    jobs: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Job results if any")
    total_jobs: Optional[int] = Field(None, description="Total jobs found")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ChatHistory(BaseModel):
    """Chat history model for conversation storage"""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # Chat identification
    chat_id: str = Field(..., description="Unique chat identifier")
    user_id: str = Field(..., description="User identifier")
    title: str = Field(default="New Chat", description="Chat title")
    
    # Messages
    messages: List[ChatMessage] = Field(default_factory=list, description="Chat messages")
    message_count: int = Field(default=0, description="Total message count")
    
    # Metadata
    language: str = Field(default="english", description="Primary language")
    tags: Optional[List[str]] = Field(default_factory=list, description="Chat tags/categories")
    
    # Statistics
    job_searches_count: int = Field(default=0, description="Number of job searches in this chat")
    jobs_found_total: int = Field(default=0, description="Total jobs found across all searches")
    avg_response_time_ms: Optional[float] = Field(None, description="Average response time")
    
    # Status
    is_active: bool = Field(default=True, description="Is chat still active")
    is_archived: bool = Field(default=False, description="Is chat archived")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# Utility models for API responses
class JobSearchRequest(BaseModel):
    """Job search request model"""
    query: str = Field(..., description="Search query")
    languages: List[str] = Field(default=["english"], description="Languages to search")
    location: Optional[str] = Field(None, description="Location filter")
    experience_level: Optional[str] = Field(None, description="Experience level filter")
    remote_only: Optional[bool] = Field(None, description="Remote jobs only")
    limit: int = Field(default=20, ge=1, le=100, description="Results limit")
    offset: int = Field(default=0, ge=0, description="Results offset")


class JobSearchResponse(BaseModel):
    """Job search response model"""
    jobs: List[JobPosting] = Field(..., description="Found jobs")
    total_count: int = Field(..., description="Total jobs matching query")
    query_info: Dict[str, Any] = Field(..., description="Query analysis")
    search_time_ms: float = Field(..., description="Search time in milliseconds")


class ChatExportRequest(BaseModel):
    """Chat export request model"""
    chat_id: str = Field(..., description="Chat ID to export")
    user_id: str = Field(..., description="User ID")
    format: str = Field(default="json", description="Export format (json, txt, md)")
    include_jobs: bool = Field(default=True, description="Include job data")


class ChatSearchRequest(BaseModel):
    """Chat search request model"""
    user_id: str = Field(..., description="User ID")
    query: Optional[str] = Field(None, description="Search query")
    limit: int = Field(default=20, ge=1, le=100, description="Results limit")
    offset: int = Field(default=0, ge=0, description="Results offset")
    include_archived: bool = Field(default=False, description="Include archived chats")


class DatabaseStats(BaseModel):
    """Database statistics model"""
    total_jobs: int
    total_training_examples: int
    total_interactions: int
    total_models: int
    total_scraping_sessions: int
    total_chat_histories: int
    total_chat_messages: int
    languages_supported: List[str]
    job_sources: List[str]
    last_scraping_session: Optional[datetime]
    database_size_mb: Optional[float]


# Validation functions
def validate_language(language: str) -> str:
    """Validate language code"""
    supported_languages = ["english", "georgian", "russian", "armenian"]
    if language.lower() not in supported_languages:
        raise ValueError(f"Unsupported language: {language}")
    return language.lower()


def validate_job_source(source: str) -> str:
    """Validate job source"""
    supported_sources = ["linkedin", "indeed", "glassdoor", "hr.ge", "jobs.ge", "synthetic"]
    if source.lower() not in supported_sources:
        raise ValueError(f"Unsupported job source: {source}")
    return source.lower()


def validate_experience_level(level: str) -> str:
    """Validate experience level"""
    supported_levels = ["entry", "junior", "mid", "senior", "lead", "executive"]
    if level.lower() not in supported_levels:
        raise ValueError(f"Unsupported experience level: {level}")
    return level.lower()


# Note: Validators would need to be implemented differently in Pydantic v2
# For now, validation is handled at the application level 