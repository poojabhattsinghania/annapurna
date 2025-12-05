"""Models for processed recipes and relationships"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from annapurna.models.base import Base
import enum


class ClusterMethodEnum(enum.Enum):
    """Method used for clustering recipes"""
    title_match = "title_match"
    ingredient_similarity = "ingredient_similarity"
    embedding_similarity = "embedding_similarity"
    manual_merge = "manual_merge"


class SimilarityMethodEnum(enum.Enum):
    """Method used for computing similarity"""
    title_fuzzy = "title_fuzzy"
    ingredient_jaccard = "ingredient_jaccard"
    embedding_cosine = "embedding_cosine"


class TagSourceEnum(enum.Enum):
    """Source of tag assignment"""
    auto_llm = "auto_llm"
    rule_engine = "rule_engine"
    manual = "manual"
    user_contributed = "user_contributed"


class RecipeCluster(Base):
    """Groups of similar recipes (e.g., all variants of 'Aloo Gobi')"""
    __tablename__ = "recipe_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_title = Column(String(255), nullable=False, index=True)
    cluster_method = Column(Enum(ClusterMethodEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    recipes = relationship("Recipe", back_populates="cluster")

    def __repr__(self):
        return f"<RecipeCluster(title='{self.canonical_title}')>"


class Recipe(Base):
    """Processed recipe data (one per scraped source)"""
    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source references (for raw data re-processing and attribution)
    scraped_content_id = Column(UUID(as_uuid=True), ForeignKey("raw_scraped_content.id"), nullable=False, index=True)
    source_creator_id = Column(UUID(as_uuid=True), ForeignKey("content_creators.id"), nullable=False, index=True)
    source_url = Column(Text, nullable=False)

    # Clustering
    recipe_cluster_id = Column(UUID(as_uuid=True), ForeignKey("recipe_clusters.id"), nullable=True, index=True)

    # Recipe data
    title = Column(String(500), nullable=False, index=True)
    title_normalized = Column(String(500), index=True)  # Lowercase, cleaned for matching
    description = Column(Text)

    # Time and servings
    prep_time_minutes = Column(Integer)
    cook_time_minutes = Column(Integer)
    total_time_minutes = Column(Integer)
    servings = Column(Integer)

    # Nutrition (optional, computed from ingredients)
    calories_per_serving = Column(Float)
    protein_grams = Column(Float)
    carbs_grams = Column(Float)
    fat_grams = Column(Float)

    # Note: Vector embeddings are stored in Qdrant, not PostgreSQL
    # Link recipes to Qdrant using recipe.id

    # Processing metadata
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    llm_model_version = Column(String(100))

    # Relationships
    scraped_content = relationship("RawScrapedContent", back_populates="recipes")
    creator = relationship("ContentCreator", back_populates="recipes")
    cluster = relationship("RecipeCluster", back_populates="recipes")
    tags = relationship("RecipeTag", back_populates="recipe", cascade="all, delete-orphan")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    steps = relationship("RecipeStep", back_populates="recipe", cascade="all, delete-orphan")

    # Similarity relationships
    similar_to = relationship(
        "RecipeSimilarity",
        foreign_keys="RecipeSimilarity.recipe_id_1",
        back_populates="recipe_1"
    )
    similar_from = relationship(
        "RecipeSimilarity",
        foreign_keys="RecipeSimilarity.recipe_id_2",
        back_populates="recipe_2"
    )

    def __repr__(self):
        return f"<Recipe(title='{self.title}', creator='{self.source_creator_id}')>"


class RecipeSimilarity(Base):
    """Pairwise similarity scores between recipes"""
    __tablename__ = "recipe_similarity"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id_1 = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)
    recipe_id_2 = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=False)  # 0.0 to 1.0
    similarity_method = Column(Enum(SimilarityMethodEnum), nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    recipe_1 = relationship("Recipe", foreign_keys=[recipe_id_1], back_populates="similar_to")
    recipe_2 = relationship("Recipe", foreign_keys=[recipe_id_2], back_populates="similar_from")

    def __repr__(self):
        return f"<RecipeSimilarity(score={self.similarity_score:.2f}, method='{self.similarity_method.value}')>"


class RecipeTag(Base):
    """Multi-dimensional tags for recipes (flexible schema)"""
    __tablename__ = "recipe_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)
    tag_dimension_id = Column(UUID(as_uuid=True), ForeignKey("tag_dimensions.id"), nullable=False, index=True)
    tag_value = Column(Text, nullable=False, index=True)  # Or JSONB for multi-select
    confidence_score = Column(Float, default=1.0)  # 0.0 to 1.0
    source = Column(Enum(TagSourceEnum), nullable=False)

    # Relationships
    recipe = relationship("Recipe", back_populates="tags")
    dimension = relationship("TagDimension", back_populates="recipe_tags")

    def __repr__(self):
        return f"<RecipeTag(dimension_id='{self.tag_dimension_id}', value='{self.tag_value}')>"


class RecipeIngredient(Base):
    """Junction table for recipe ingredients"""
    __tablename__ = "recipe_ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients_master.id"), nullable=False, index=True)
    quantity = Column(Float)
    unit = Column(String(50))  # grams, ml, pieces, cups, tsp, tbsp
    original_text = Column(Text)  # "2 katori aloo" - preserve original

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("IngredientMaster", back_populates="recipe_ingredients")

    def __repr__(self):
        return f"<RecipeIngredient(ingredient_id='{self.ingredient_id}', qty={self.quantity} {self.unit})>"


class RecipeStep(Base):
    """Step-by-step instructions for recipes"""
    __tablename__ = "recipe_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)

    # Optional: time and media
    estimated_time_minutes = Column(Integer)
    image_url = Column(Text)

    # Relationships
    recipe = relationship("Recipe", back_populates="steps")

    def __repr__(self):
        return f"<RecipeStep(recipe_id='{self.recipe_id}', step={self.step_number})>"
