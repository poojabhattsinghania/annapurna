"""Qdrant vector database client for recipe embeddings"""

from typing import List, Dict, Optional, Tuple
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import google.generativeai as genai
from annapurna.config import settings

# Configure Gemini for embedding generation
genai.configure(api_key=settings.gemini_api_key)


class QdrantVectorDB:
    """Client for managing recipe embeddings in Qdrant"""

    COLLECTION_NAME = "recipe_embeddings"
    VECTOR_SIZE = 768  # Gemini text-embedding-004 dimension

    def __init__(self):
        """Initialize Qdrant client"""
        self.client = QdrantClient(url=settings.qdrant_url)
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        if self.COLLECTION_NAME not in collection_names:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            print(f"Created Qdrant collection: {self.COLLECTION_NAME}")

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for given text using Gemini

        Args:
            text: Text to embed (recipe title + description + tags)

        Returns:
            List of floats representing the 768-dimensional embedding vector
        """
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
                title="Recipe Embedding"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

    def create_recipe_embedding(
        self,
        recipe_id: str,
        title: str,
        description: str,
        tags: List[str] = None
    ) -> bool:
        """
        Generate and store embedding for a recipe (combines generation + storage)

        Args:
            recipe_id: Unique recipe ID (UUID string)
            title: Recipe title
            description: Recipe description
            tags: Optional list of tag values (all strings, multi-select tags should be flattened)

        Returns:
            True if successful, False otherwise
        """
        # Validate that all tags are strings
        if tags:
            for i, tag in enumerate(tags):
                if not isinstance(tag, str):
                    print(f"⚠️  Warning: Tag at index {i} is not a string: {tag} (type: {type(tag)})")
                    print(f"   Tag list: {tags}")
                    return False

        # Combine title, description, and tags for embedding
        tags_str = ", ".join(tags) if tags else ""
        text_to_embed = f"{title}. {description}. Tags: {tags_str}"

        # Generate embedding using Gemini
        print(f"  Generating embedding for: {title[:50]}...")
        embedding = self.generate_embedding(text_to_embed)

        if not embedding:
            print(f"  ✗ Failed to generate embedding for recipe: {title}")
            return False

        # Store in Qdrant
        try:
            point_id = str(uuid.uuid4())  # Generate UUID for Qdrant point ID

            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,  # Qdrant point ID (internal)
                        vector=embedding,
                        payload={
                            "recipe_id": recipe_id,  # Recipe UUID (for lookups)
                            "title": title,
                            "description": description,
                            "tags": tags or []
                        }
                    )
                ]
            )
            print(f"  ✓ Stored embedding in Qdrant (recipe_id: {recipe_id[:8]}...)")
            return True
        except Exception as e:
            print(f"  ✗ Error storing embedding in Qdrant: {e}")
            print(f"     Recipe: {title}")
            print(f"     Tags: {tags}")
            import traceback
            traceback.print_exc()
            return False

    def upsert_embedding(
        self,
        recipe_id: str,
        embedding: List[float],
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Insert or update a recipe embedding

        Args:
            recipe_id: UUID of the recipe
            embedding: 384-dimensional vector
            metadata: Optional metadata (title, tags, etc.)

        Returns:
            Success boolean
        """
        try:
            # Validate embedding dimension
            if len(embedding) != self.VECTOR_SIZE:
                raise ValueError(f"Embedding must be {self.VECTOR_SIZE} dimensions, got {len(embedding)}")

            # Prepare payload
            payload = metadata or {}
            payload["recipe_id"] = str(recipe_id)

            # Create point
            point = PointStruct(
                id=str(uuid.uuid4()),  # Qdrant point ID (different from recipe_id)
                vector=embedding,
                payload=payload
            )

            # Upsert to Qdrant
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point]
            )

            return True

        except Exception as e:
            print(f"Error upserting embedding for recipe {recipe_id}: {str(e)}")
            return False

    def batch_upsert_embeddings(
        self,
        embeddings: List[Tuple[str, List[float], Dict]]
    ) -> int:
        """
        Batch insert/update multiple embeddings

        Args:
            embeddings: List of (recipe_id, embedding, metadata) tuples

        Returns:
            Number of successfully inserted embeddings
        """
        points = []

        for recipe_id, embedding, metadata in embeddings:
            try:
                if len(embedding) != self.VECTOR_SIZE:
                    print(f"Skipping recipe {recipe_id}: Invalid embedding dimension")
                    continue

                payload = metadata or {}
                payload["recipe_id"] = str(recipe_id)

                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload=payload
                )
                points.append(point)

            except Exception as e:
                print(f"Error preparing embedding for recipe {recipe_id}: {str(e)}")
                continue

        if points:
            try:
                self.client.upsert(
                    collection_name=self.COLLECTION_NAME,
                    points=points
                )
                return len(points)
            except Exception as e:
                print(f"Error batch upserting embeddings: {str(e)}")
                return 0

        return 0

    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_conditions: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar recipes by embedding

        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filter_conditions: Optional metadata filters

        Returns:
            List of results with recipe_id, score, and metadata
        """
        try:
            # Build filter if conditions provided
            query_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                query_filter = Filter(must=conditions) if conditions else None

            # Search
            results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "recipe_id": result.payload.get("recipe_id"),
                    "score": result.score,
                    "metadata": result.payload
                })

            return formatted_results

        except Exception as e:
            print(f"Error searching embeddings: {str(e)}")
            return []

    def get_embedding(self, recipe_id: str) -> Optional[List[float]]:
        """
        Retrieve embedding for a specific recipe

        Args:
            recipe_id: Recipe UUID

        Returns:
            Embedding vector or None if not found
        """
        try:
            # Search by recipe_id in payload
            results = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="recipe_id",
                            match=MatchValue(value=str(recipe_id))
                        )
                    ]
                ),
                limit=1
            )

            if results[0]:  # results is (points, next_page_offset)
                return results[0][0].vector

            return None

        except Exception as e:
            print(f"Error retrieving embedding for recipe {recipe_id}: {str(e)}")
            return None

    def delete_embedding(self, recipe_id: str) -> bool:
        """
        Delete embedding for a recipe

        Args:
            recipe_id: Recipe UUID

        Returns:
            Success boolean
        """
        try:
            # Find point ID by recipe_id
            results = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="recipe_id",
                            match=MatchValue(value=str(recipe_id))
                        )
                    ]
                ),
                limit=1
            )

            if results[0]:
                point_id = results[0][0].id
                self.client.delete(
                    collection_name=self.COLLECTION_NAME,
                    points_selector=[point_id]
                )
                return True

            return False

        except Exception as e:
            print(f"Error deleting embedding for recipe {recipe_id}: {str(e)}")
            return False

    def count_embeddings(self) -> int:
        """Get total number of embeddings stored"""
        try:
            collection_info = self.client.get_collection(self.COLLECTION_NAME)
            return collection_info.points_count
        except Exception as e:
            print(f"Error counting embeddings: {str(e)}")
            return 0

    def health_check(self) -> bool:
        """Check if Qdrant is accessible"""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            print(f"Qdrant health check failed: {str(e)}")
            return False


# Singleton instance
_qdrant_client = None


def get_qdrant_client() -> QdrantVectorDB:
    """Get or create Qdrant client singleton"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantVectorDB()
    return _qdrant_client
