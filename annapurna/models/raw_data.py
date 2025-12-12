"""Models for raw scraped data and logging"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from annapurna.models.base import Base
import enum


class SourceTypeEnum(enum.Enum):
    """Type of content source"""
    youtube_video = "youtube_video"
    youtube_playlist = "youtube_playlist"
    website = "website"


class ScrapingStatusEnum(enum.Enum):
    """Status of scraping attempt"""
    success = "success"
    failed = "failed"
    rate_limited = "rate_limited"
    blocked = "blocked"


class ErrorTypeEnum(enum.Enum):
    """Type of scraping error"""
    network = "network"
    parsing = "parsing"
    auth = "auth"
    content_unavailable = "content_unavailable"


class RawScrapedContent(Base):
    """Immutable raw data from scraping (source of truth)"""
    __tablename__ = "raw_scraped_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(Text, nullable=False, unique=True, index=True)
    source_type = Column(Enum(SourceTypeEnum), nullable=False)
    source_creator_id = Column(UUID(as_uuid=True), ForeignKey("content_creators.id"), nullable=False, index=True)
    source_platform = Column(String(50), nullable=False)

    # Raw data fields
    raw_transcript = Column(Text)  # For YouTube videos
    raw_html = Column(Text)  # For websites
    raw_metadata_json = Column(JSONB)  # Video description, Schema.org data, etc.

    # Metadata
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    scraper_version = Column(String(50), nullable=False)

    # Processing tracking
    processing_attempts = Column(Integer, default=0, nullable=False)
    processing_failed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)

    # Relationships
    creator = relationship("ContentCreator", back_populates="scraped_content")
    recipes = relationship("Recipe", back_populates="scraped_content")

    def __repr__(self):
        return f"<RawScrapedContent(url='{self.source_url[:50]}...', type='{self.source_type.value}')>"


class ScrapingLog(Base):
    """Log of all scraping attempts (success and failures)"""
    __tablename__ = "scraping_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False, index=True)
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = Column(Enum(ScrapingStatusEnum), nullable=False, index=True)
    error_message = Column(Text)
    error_type = Column(Enum(ErrorTypeEnum))
    retry_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<ScrapingLog(url='{self.url[:50]}...', status='{self.status.value}')>"
