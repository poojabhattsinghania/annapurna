"""FastAPI application for Project Annapurna"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from annapurna.config import settings
from annapurna.models.base import get_db
from annapurna.api import recipes, search, scraping, processing, tasks, cache_management, monitoring, feedback

# Create FastAPI app
app = FastAPI(
    title="Project Annapurna",
    description="The Intelligent Recipe Brain - Semantic search-powered recipe database for Indian cuisine",
    version="1.0.0",
    docs_url=f"/{settings.api_version}/docs",
    redoc_url=f"/{settings.api_version}/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

# Include routers
app.include_router(recipes.router, prefix=f"/{settings.api_version}/recipes", tags=["Recipes"])
app.include_router(search.router, prefix=f"/{settings.api_version}/search", tags=["Search"])
app.include_router(scraping.router, prefix=f"/{settings.api_version}/scrape", tags=["Scraping"])
app.include_router(processing.router, prefix=f"/{settings.api_version}/process", tags=["Processing"])
app.include_router(tasks.router, prefix=f"/{settings.api_version}/tasks", tags=["Async Tasks"])
app.include_router(cache_management.router, prefix=f"/{settings.api_version}/cache", tags=["Cache Management"])
app.include_router(monitoring.router, prefix=f"/{settings.api_version}/monitoring", tags=["Monitoring"])
app.include_router(feedback.router, prefix=f"/{settings.api_version}/feedback", tags=["Feedback"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "annapurna.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )
