"""
Vector Embeddings Service for Recipe Similarity Search

This service generates embeddings for recipes using Gemini's embedding model
and stores them in Qdrant vector database for similarity search.
"""

import os
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import google.generativeai as genai
from annapurna.config import settings

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

class VectorEmbeddingsService:
    """Service for generating and managing recipe embeddings"""

    def __init__(self):
        self.qdrant_client = QdrantClient(url=os.getenv('QDRANT_URL', 'http://localhost:6333'))
        self.collection_name = "recipe_embeddings"
        self.embedding_dim = 768  # text-embedding-004 dimension

        # Initialize collection if doesn't exist
        self._init_collection()

    def _init_collection(self):
        """Initialize Qdrant collection for recipe embeddings"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                print(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            print(f"Error initializing Qdrant collection: {e}")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for given text using Gemini

        Args:
            text: Text to embed (recipe title + description)

        Returns:
            List of floats representing the embedding vector
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

    def create_recipe_embedding(self, recipe_id: int, title: str, description: str, tags: List[str] = None) -> bool:
        """
        Create and store embedding for a recipe

        Args:
            recipe_id: Unique recipe ID
            title: Recipe title
            description: Recipe description
            tags: Optional list of tags

        Returns:
            True if successful, False otherwise
        """
        # Combine title, description, and tags for embedding
        tags_str = ", ".join(tags) if tags else ""
        text_to_embed = f"{title}. {description}. Tags: {tags_str}"

        # Generate embedding
        embedding = self.generate_embedding(text_to_embed)

        if not embedding:
            return False

        # Store in Qdrant
        try:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=recipe_id,
                        vector=embedding,
                        payload={
                            "recipe_id": recipe_id,
                            "title": title,
                            "description": description,
                            "tags": tags or []
                        }
                    )
                ]
            )
            return True
        except Exception as e:
            print(f"Error storing embedding in Qdrant: {e}")
            return False

    def search_similar_recipes(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for recipes similar to the given query

        Args:
            query: Search query (can be natural language)
            limit: Number of results to return

        Returns:
            List of similar recipes with scores
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query)

        if not query_embedding:
            return []

        # Search in Qdrant
        try:
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit
            )

            # Format results
            similar_recipes = []
            for result in results:
                similar_recipes.append({
                    "recipe_id": result.payload["recipe_id"],
                    "title": result.payload["title"],
                    "description": result.payload["description"],
                    "tags": result.payload.get("tags", []),
                    "similarity_score": result.score
                })

            return similar_recipes
        except Exception as e:
            print(f"Error searching similar recipes: {e}")
            return []

    def find_similar_by_recipe_id(self, recipe_id: int, limit: int = 10) -> List[Dict]:
        """
        Find recipes similar to a given recipe

        Args:
            recipe_id: ID of the recipe to find similar ones for
            limit: Number of results to return

        Returns:
            List of similar recipes
        """
        try:
            # Get the recipe's embedding
            recipe_point = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=[recipe_id]
            )

            if not recipe_point:
                return []

            # Search using the recipe's embedding
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=recipe_point[0].vector,
                limit=limit + 1  # +1 to exclude the recipe itself
            )

            # Format and exclude the recipe itself
            similar_recipes = []
            for result in results:
                if result.payload["recipe_id"] != recipe_id:
                    similar_recipes.append({
                        "recipe_id": result.payload["recipe_id"],
                        "title": result.payload["title"],
                        "description": result.payload["description"],
                        "tags": result.payload.get("tags", []),
                        "similarity_score": result.score
                    })

            return similar_recipes[:limit]
        except Exception as e:
            print(f"Error finding similar recipes: {e}")
            return []

    def delete_recipe_embedding(self, recipe_id: int) -> bool:
        """Delete embedding for a recipe"""
        try:
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=[recipe_id]
            )
            return True
        except Exception as e:
            print(f"Error deleting embedding: {e}")
            return False
