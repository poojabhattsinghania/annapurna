"""Pydantic schemas for API requests/responses"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


# Recipe schemas
class IngredientResponse(BaseModel):
    standard_name: str
    quantity: Optional[float]
    unit: Optional[str]
    original_text: Optional[str]

    class Config:
        from_attributes = True


class RecipeStepResponse(BaseModel):
    step_number: int
    instruction: str
    estimated_time_minutes: Optional[int]

    class Config:
        from_attributes = True


class RecipeTagResponse(BaseModel):
    dimension_name: str
    tag_value: str
    confidence_score: float

    class Config:
        from_attributes = True


class RecipeResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    source_url: str
    source_creator: str
    prep_time_minutes: Optional[int]
    cook_time_minutes: Optional[int]
    total_time_minutes: Optional[int]
    servings: Optional[int]
    ingredients: List[IngredientResponse] = []
    steps: List[RecipeStepResponse] = []
    tags: List[RecipeTagResponse] = []

    class Config:
        from_attributes = True


class RecipeSummary(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    source_creator: str
    total_time_minutes: Optional[int]
    servings: Optional[int]

    class Config:
        from_attributes = True


# Search schemas
class SearchFilters(BaseModel):
    # Multi-dimensional filters
    spice_level: Optional[List[str]] = None
    texture: Optional[List[str]] = None
    complexity: Optional[List[str]] = None
    meal_slot: Optional[List[str]] = None
    region: Optional[List[str]] = None

    # Boolean filters
    jain: Optional[bool] = None
    vrat: Optional[bool] = None
    diabetic_friendly: Optional[bool] = None
    high_protein: Optional[bool] = None
    gluten_free: Optional[bool] = None
    vegan: Optional[bool] = None

    # Range filters
    max_time_minutes: Optional[int] = None
    min_servings: Optional[int] = None
    max_servings: Optional[int] = None

    # Creator filter
    creator_name: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    filters: Optional[SearchFilters] = None
    limit: int = Field(default=20, le=100)
    offset: int = Field(default=0, ge=0)
    search_type: str = Field(default="hybrid", pattern="^(semantic|sql|hybrid)$")


class SearchResult(BaseModel):
    recipe: RecipeSummary
    relevance_score: float
    match_reason: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_count: int
    query: str
    filters_applied: Optional[Dict[str, Any]]


# Scraping schemas
class ScrapeRequest(BaseModel):
    url: str = Field(..., description="URL to scrape (YouTube video/playlist or website)")
    creator_name: str = Field(..., description="Content creator name (must exist in database)")
    max_items: int = Field(default=50, le=500, description="Max items to scrape (for playlists)")


class ScrapeResponse(BaseModel):
    success: bool
    message: str
    scraped_ids: List[uuid.UUID] = []
    stats: Dict[str, int] = {}


# Processing schemas
class ProcessRequest(BaseModel):
    raw_content_id: Optional[uuid.UUID] = None
    batch_size: int = Field(default=10, le=100)


class ProcessResponse(BaseModel):
    success: bool
    message: str
    processed_ids: List[uuid.UUID] = []
    stats: Dict[str, int] = {}


# Creator schemas
class ContentCreatorCreate(BaseModel):
    name: str
    platform: str
    base_url: str
    language: List[str] = []
    specialization: List[str] = []


class ContentCreatorResponse(BaseModel):
    id: uuid.UUID
    name: str
    platform: str
    base_url: str
    language: List[str]
    specialization: List[str]
    is_active: bool
    added_at: datetime

    class Config:
        from_attributes = True
