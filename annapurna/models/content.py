"""Models for content sources and categories"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, ARRAY, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from annapurna.models.base import Base
import enum


class PlatformEnum(enum.Enum):
    """Supported platforms for content scraping"""
    youtube = "youtube"
    website = "website"
    instagram = "instagram"
    blog = "blog"


class ContentCreator(Base):
    """Content creators/sources (YouTubers, bloggers, websites)"""
    __tablename__ = "content_creators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    platform = Column(Enum(PlatformEnum), nullable=False)
    base_url = Column(Text, nullable=False)
    language = Column(ARRAY(String), nullable=False, default=[])
    specialization = Column(ARRAY(String), nullable=False, default=[])
    reliability_score = Column(Float, default=1.0)  # 0.0 to 1.0
    is_active = Column(Boolean, default=True, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    scraped_content = relationship("RawScrapedContent", back_populates="creator")
    recipes = relationship("Recipe", back_populates="creator")

    def __repr__(self):
        return f"<ContentCreator(name='{self.name}', platform='{self.platform.value}')>"


class ContentCategory(Base):
    """Hierarchical category system for recipes"""
    __tablename__ = "content_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_name = Column(String(255), nullable=False, index=True)
    parent_category_id = Column(UUID(as_uuid=True), ForeignKey("content_categories.id"), nullable=True)
    description = Column(Text)
    scraping_priority = Column(Integer, default=3)  # 1=high, 5=low
    is_active = Column(Boolean, default=True, index=True)

    # Self-referential relationship for hierarchy
    parent = relationship("ContentCategory", remote_side=[id], backref="children")

    def __repr__(self):
        return f"<ContentCategory(name='{self.category_name}')>"
