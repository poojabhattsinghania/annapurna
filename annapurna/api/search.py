"""Search endpoints with hybrid semantic + SQL filtering"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List

from annapurna.models.base import get_db
from annapurna.models.recipe import Recipe, RecipeTag
from annapurna.models.content import ContentCreator
from annapurna.models.taxonomy import TagDimension
from annapurna.api.schemas import SearchRequest, SearchResponse, SearchResult, RecipeSummary
from annapurna.utils.qdrant_client import QdrantVectorDB
from annapurna.utils.cache import cached, cache

router = APIRouter()


class HybridSearch:
    """Hybrid search combining semantic search and SQL filters"""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_gen = None

    def _init_embedding_generator(self):
        """Lazy load embedding generator"""
        if self.embedding_gen is None:
            self.embedding_gen = QdrantVectorDB()

    def apply_sql_filters(self, query, filters):
        """Apply SQL filters to query"""
        if not filters:
            return query

        # Boolean tag filters
        tag_filters = []

        if filters.jain is not None:
            tag_filters.append(('health_jain', 'true' if filters.jain else 'false'))

        if filters.vrat is not None:
            tag_filters.append(('health_vrat', 'true' if filters.vrat else 'false'))

        if filters.diabetic_friendly is not None:
            tag_filters.append(('health_diabetic_friendly', 'true' if filters.diabetic_friendly else 'false'))

        if filters.high_protein is not None:
            tag_filters.append(('health_high_protein', 'true' if filters.high_protein else 'false'))

        if filters.gluten_free is not None:
            tag_filters.append(('health_gluten_free', 'true' if filters.gluten_free else 'false'))

        # Apply tag filters
        for dim_name, required_value in tag_filters:
            dimension = self.db.query(TagDimension).filter_by(
                dimension_name=dim_name
            ).first()

            if dimension:
                query = query.join(RecipeTag).filter(
                    RecipeTag.tag_dimension_id == dimension.id,
                    RecipeTag.tag_value == required_value
                )

        # Multi-select filters
        if filters.spice_level:
            dimension = self.db.query(TagDimension).filter_by(
                dimension_name='vibe_spice'
            ).first()
            if dimension:
                query = query.join(RecipeTag).filter(
                    RecipeTag.tag_dimension_id == dimension.id,
                    RecipeTag.tag_value.in_(filters.spice_level)
                )

        if filters.texture:
            dimension = self.db.query(TagDimension).filter_by(
                dimension_name='vibe_texture'
            ).first()
            if dimension:
                query = query.join(RecipeTag).filter(
                    RecipeTag.tag_dimension_id == dimension.id,
                    RecipeTag.tag_value.in_(filters.texture)
                )

        if filters.region:
            dimension = self.db.query(TagDimension).filter_by(
                dimension_name='context_region'
            ).first()
            if dimension:
                query = query.join(RecipeTag).filter(
                    RecipeTag.tag_dimension_id == dimension.id,
                    RecipeTag.tag_value.in_(filters.region)
                )

        # Range filters
        if filters.max_time_minutes:
            query = query.filter(
                Recipe.total_time_minutes <= filters.max_time_minutes
            )

        if filters.min_servings:
            query = query.filter(
                Recipe.servings >= filters.min_servings
            )

        if filters.max_servings:
            query = query.filter(
                Recipe.servings <= filters.max_servings
            )

        # Creator filter
        if filters.creator_name:
            query = query.join(ContentCreator).filter(
                ContentCreator.name.ilike(f"%{filters.creator_name}%")
            )

        return query

    def semantic_search(self, query_text: str, filters, limit: int, offset: int):
        """Pure semantic search with filters"""
        self._init_embedding_generator()

        # Get semantic matches
        similar_recipes = self.embedding_gen.find_similar(
            query_text,
            self.db,
            limit=limit * 2,  # Get extra to account for filtering
            threshold=0.3
        )

        # Apply SQL filters manually
        filtered_results = []
        for recipe, score in similar_recipes:
            # Check filters
            passes = self._check_recipe_filters(recipe, filters)
            if passes:
                filtered_results.append((recipe, score))

        # Paginate
        paginated = filtered_results[offset:offset + limit]

        return paginated, len(filtered_results)

    def sql_search(self, query_text: str, filters, limit: int, offset: int):
        """Pure SQL search (keyword matching + filters)"""
        query = self.db.query(Recipe)

        # Keyword matching on title and description
        search_filter = or_(
            Recipe.title.ilike(f"%{query_text}%"),
            Recipe.description.ilike(f"%{query_text}%")
        )
        query = query.filter(search_filter)

        # Apply filters
        query = self.apply_sql_filters(query, filters)

        # Get total count
        total = query.count()

        # Paginate
        results = query.offset(offset).limit(limit).all()

        # Convert to (recipe, score) format (score = 1.0 for exact matches)
        scored_results = [(recipe, 1.0) for recipe in results]

        return scored_results, total

    # @cached('search_hybrid', ttl=1800)  # Cache for 30 minutes - DISABLED: causes serialization issue with self
    def hybrid_search(self, query_text: str, filters, limit: int, offset: int):
        """
        Hybrid search: Semantic search + SQL filters

        Strategy:
        1. Use Qdrant for semantic search
        2. Apply hard SQL filters to the results
        3. Combine and rank results
        """
        self._init_embedding_generator()
        from annapurna.utils.qdrant_client import get_qdrant_client

        # Get semantic candidates from Qdrant (get more than limit for filtering)
        query_embedding = self.embedding_gen.generate_embedding(query_text)
        qdrant = get_qdrant_client()

        # Search with larger limit to account for filters
        qdrant_results = qdrant.search_similar(
            query_embedding=query_embedding,  # VectorEmbeddingsService returns list directly
            limit=limit * 5,  # Get 5x more to allow for filtering
            score_threshold=0.3
        )

        if not qdrant_results:
            return [], 0

        # Get recipe IDs from Qdrant results (filter out invalid UUIDs and deduplicate)
        import uuid
        valid_recipe_ids = []
        seen_ids = set()

        for result in qdrant_results:
            rid = result["recipe_id"]
            try:
                # Try to convert to UUID (handles both string UUIDs and valid formats)
                recipe_uuid = None
                if isinstance(rid, str):
                    recipe_uuid = uuid.UUID(rid)
                elif isinstance(rid, uuid.UUID):
                    recipe_uuid = rid

                # Only add if not seen before (deduplicate)
                if recipe_uuid and str(recipe_uuid) not in seen_ids:
                    valid_recipe_ids.append(recipe_uuid)
                    seen_ids.add(str(recipe_uuid))
                # Skip integers and other invalid formats
            except (ValueError, AttributeError):
                continue

        if not valid_recipe_ids:
            return [], 0

        # Fetch recipes from database and apply SQL filters
        query = self.db.query(Recipe).filter(
            Recipe.id.in_(valid_recipe_ids)
        )

        # Apply SQL filters
        query = self.apply_sql_filters(query, filters)
        filtered_recipes = query.all()

        # Map recipe_id to BEST score from Qdrant (in case of duplicates, keep highest)
        score_map = {}
        for result in qdrant_results:
            rid = result["recipe_id"]
            score = result["score"]
            if rid not in score_map or score > score_map[rid]:
                score_map[rid] = score

        # Create scored results with recipes that passed filters
        scored_results = []
        for recipe in filtered_recipes:
            score = score_map.get(str(recipe.id), 0.0)
            scored_results.append((recipe, score))

        # Sort by score (already sorted from Qdrant, but ensure order)
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Paginate
        total = len(scored_results)
        paginated = scored_results[offset:offset + limit]

        return paginated, total

    def _check_recipe_filters(self, recipe: Recipe, filters) -> bool:
        """Check if recipe passes all filters (for manual filtering)"""
        if not filters:
            return True

        # Time filter
        if filters.max_time_minutes and recipe.total_time_minutes:
            if recipe.total_time_minutes > filters.max_time_minutes:
                return False

        # Servings filter
        if filters.min_servings and recipe.servings:
            if recipe.servings < filters.min_servings:
                return False

        if filters.max_servings and recipe.servings:
            if recipe.servings > filters.max_servings:
                return False

        # Creator filter
        if filters.creator_name:
            if filters.creator_name.lower() not in recipe.creator.name.lower():
                return False

        return True


@router.post("/", response_model=SearchResponse)
def search_recipes(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search recipes with hybrid semantic + SQL filtering

    Supports three search types:
    - semantic: Pure vector similarity search
    - sql: Keyword matching + SQL filters
    - hybrid: Semantic search with SQL filters (recommended)
    """
    hybrid_search = HybridSearch(db)

    # Execute search based on type
    if request.search_type == "semantic":
        results, total = hybrid_search.semantic_search(
            request.query,
            request.filters,
            request.limit,
            request.offset
        )
    elif request.search_type == "sql":
        results, total = hybrid_search.sql_search(
            request.query,
            request.filters,
            request.limit,
            request.offset
        )
    else:  # hybrid
        results, total = hybrid_search.hybrid_search(
            request.query,
            request.filters,
            request.limit,
            request.offset
        )

    # Format response
    search_results = []
    for recipe, score in results:
        search_results.append(SearchResult(
            recipe=RecipeSummary(
                id=recipe.id,
                title=recipe.title,
                description=recipe.description,
                source_creator=recipe.creator.name if recipe.creator else "Unknown",
                total_time_minutes=recipe.total_time_minutes,
                servings=recipe.servings
            ),
            relevance_score=round(score, 3),
            match_reason=f"Semantic similarity: {score:.1%}" if score < 1.0 else "Exact match"
        ))

    return SearchResponse(
        results=search_results,
        total_count=total,
        query=request.query,
        filters_applied=request.filters.dict() if request.filters else None
    )


@router.get("/filters")
def get_available_filters(db: Session = Depends(get_db)):
    """Get all available filter options from taxonomy"""
    dimensions = db.query(TagDimension).filter_by(is_active=True).all()

    filters = {}
    for dim in dimensions:
        filters[dim.dimension_name] = {
            "category": dim.dimension_category.value,
            "data_type": dim.data_type.value,
            "allowed_values": dim.allowed_values,
            "description": dim.description
        }

    return filters
