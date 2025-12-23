"""Service for generating user taste profile embeddings for RAG-based recommendations"""

from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from annapurna.models.user_preferences import UserProfile
from annapurna.utils.qdrant_client import get_qdrant_client


# Cache duration for user taste embeddings (regenerate after this period)
EMBEDDING_CACHE_HOURS = 24


class UserTasteEmbeddingService:
    """
    Generate and manage user taste embeddings for semantic recipe matching.

    Converts the user's taste profile (from onboarding questionnaire) into a
    768-dimensional embedding that can be compared against recipe embeddings
    for personalized recommendations.
    """

    def __init__(self, db: Session):
        self.db = db
        self.qdrant = get_qdrant_client()

    def get_user_embedding(self, user_id: str, force_refresh: bool = False) -> Optional[List[float]]:
        """
        Get embedding for user's taste profile.

        Uses cached embedding if available and not stale, otherwise generates new one.

        Args:
            user_id: User ID string
            force_refresh: If True, regenerate even if cached

        Returns:
            768-dimensional embedding vector, or None if profile not found
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            return None

        # Check if we have a cached embedding that's still fresh
        if not force_refresh:
            cached = self._get_cached_embedding(user_id)
            if cached:
                return cached

        # Generate new embedding from profile
        return self._generate_and_cache_embedding(profile)

    def _get_cached_embedding(self, user_id: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding from Qdrant user_taste_embeddings collection.

        Returns None if not found or stale.
        """
        try:
            # Search for user embedding by user_id in payload
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            results = self.qdrant.client.scroll(
                collection_name="user_taste_embeddings",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=1,
                with_vectors=True
            )

            if results[0]:
                point = results[0][0]
                # Check if embedding is still fresh
                cached_at = point.payload.get("cached_at")
                if cached_at:
                    cached_time = datetime.fromisoformat(cached_at)
                    if datetime.utcnow() - cached_time < timedelta(hours=EMBEDDING_CACHE_HOURS):
                        return point.vector

            return None

        except Exception as e:
            # Collection might not exist yet, that's okay
            print(f"Note: Could not retrieve cached embedding: {e}")
            return None

    def _generate_and_cache_embedding(self, profile: UserProfile) -> Optional[List[float]]:
        """
        Generate embedding from user profile and cache it.
        """
        # Build taste profile text
        profile_text = self._build_taste_profile_text(profile)

        if not profile_text:
            return None

        # Generate embedding using Gemini (same as recipes)
        embedding = self.qdrant.generate_embedding(profile_text)

        if not embedding:
            print(f"Failed to generate embedding for user {profile.user_id}")
            return None

        # Cache the embedding
        self._cache_embedding(profile.user_id, embedding, profile_text)

        return embedding

    def _build_taste_profile_text(self, profile: UserProfile) -> str:
        """
        Convert user profile fields into a natural language description
        that can be embedded and compared against recipe embeddings.

        This creates a "synthetic recipe description" that captures what
        kind of recipes this user would enjoy.
        """
        parts = []

        # Diet type
        diet_descriptions = {
            'pure_veg': 'Looking for pure vegetarian Indian recipes, no eggs.',
            'veg_eggs': 'Looking for vegetarian Indian recipes, eggs are okay.',
            'non_veg': 'Looking for Indian recipes including non-vegetarian options.',
            'vegetarian': 'Looking for vegetarian Indian recipes.'
        }
        parts.append(diet_descriptions.get(profile.diet_type, 'Looking for Indian recipes.'))

        # Dietary restrictions
        restrictions = []
        if profile.no_beef:
            restrictions.append('no beef')
        if profile.no_pork:
            restrictions.append('no pork')
        if profile.is_halal:
            restrictions.append('halal only')
        if profile.is_jain or profile.allium_status == 'no_both':
            restrictions.append('no onion and garlic (Jain)')
        elif profile.allium_status == 'no_onion':
            restrictions.append('no onion')
        elif profile.allium_status == 'no_garlic':
            restrictions.append('no garlic')
        if profile.is_gluten_free:
            restrictions.append('gluten-free')
        if profile.is_dairy_free:
            restrictions.append('dairy-free')

        if restrictions:
            parts.append(f"Dietary restrictions: {', '.join(restrictions)}.")

        # Regional preferences
        if profile.primary_regional_influence:
            regions = profile.primary_regional_influence
            region_text = {
                'north_indian': 'North Indian',
                'south_indian': 'South Indian',
                'bengali': 'Bengali',
                'gujarati': 'Gujarati',
                'maharashtrian': 'Maharashtrian',
                'punjabi': 'Punjabi',
                'rajasthani': 'Rajasthani',
                'kerala': 'Kerala',
                'tamil': 'Tamil',
                'andhra': 'Andhra',
                'hyderabadi': 'Hyderabadi',
                'kashmiri': 'Kashmiri',
                'goan': 'Goan',
                'chettinad': 'Chettinad'
            }
            formatted_regions = [region_text.get(r, r.replace('_', ' ').title()) for r in regions]
            parts.append(f"Prefers {' and '.join(formatted_regions)} cuisine.")

        # Heat/spice level
        heat_descriptions = {
            1: 'Prefers very mild, kid-friendly spice levels.',
            2: 'Prefers mild spice, gentle flavors.',
            3: 'Enjoys medium spice level, standard Indian heat.',
            4: 'Loves spicy food, high heat preferred.',
            5: 'Craves very hot and spicy dishes, maximum heat.'
        }
        if profile.heat_level:
            parts.append(heat_descriptions.get(profile.heat_level, ''))

        # Sweetness in savory
        if profile.sweetness_in_savory:
            sweetness_text = {
                'never': 'Does not like sweetness in savory dishes.',
                'subtle': 'Enjoys subtle sweetness in savory dishes like Gujarati style.',
                'regular': 'Likes regular sweetness in savory dishes.'
            }
            if profile.sweetness_in_savory in sweetness_text:
                parts.append(sweetness_text[profile.sweetness_in_savory])

        # Gravy preferences
        if profile.gravy_preferences:
            gravy_text = {
                'dry': 'dry preparations',
                'semi_dry': 'semi-dry dishes',
                'medium': 'medium gravy',
                'thin': 'thin gravy curries',
                'mixed': 'variety of gravy types'
            }
            prefs = [gravy_text.get(g, g) for g in profile.gravy_preferences]
            parts.append(f"Prefers {', '.join(prefs)}.")

        # Fat richness
        if profile.fat_richness:
            richness_text = {
                'light': 'Prefers light, healthy cooking with less oil and ghee.',
                'medium': 'Enjoys balanced richness, moderate use of fats.',
                'rich': 'Loves rich, indulgent dishes with generous ghee and cream.'
            }
            if profile.fat_richness in richness_text:
                parts.append(richness_text[profile.fat_richness])

        # Cooking fat preference
        if profile.cooking_fat and profile.cooking_fat != 'mixed':
            fat_text = {
                'ghee': 'Prefers cooking with ghee.',
                'mustard': 'Prefers mustard oil for cooking (Bengali/Eastern style).',
                'coconut': 'Prefers coconut oil for cooking (South Indian style).',
                'vegetable': 'Uses vegetable/neutral oil for cooking.'
            }
            if profile.cooking_fat in fat_text:
                parts.append(fat_text[profile.cooking_fat])

        # Primary staple
        if profile.primary_staple:
            staple_text = {
                'rice': 'Rice is the primary staple, prefers rice-based meals.',
                'roti': 'Roti/chapati is the primary staple, prefers bread-based meals.',
                'both': 'Enjoys both rice and roti equally.'
            }
            if profile.primary_staple in staple_text:
                parts.append(staple_text[profile.primary_staple])

        # Signature masalas (indicates regional cooking style)
        if profile.signature_masalas:
            masala_text = {
                'garam_masala': 'garam masala',
                'sambar_powder': 'sambar powder (South Indian)',
                'goda_masala': 'goda masala (Maharashtrian)',
                'panch_phoron': 'panch phoron (Bengali)',
                'rasam_powder': 'rasam powder (South Indian)',
                'chole_masala': 'chole masala (North Indian)',
                'kitchen_king': 'kitchen king masala',
                'pav_bhaji_masala': 'pav bhaji masala',
                'biryani_masala': 'biryani masala'
            }
            formatted_masalas = [masala_text.get(m, m) for m in profile.signature_masalas]
            parts.append(f"Uses {', '.join(formatted_masalas)} in cooking.")

        # Health modifications
        if profile.health_modifications:
            health_text = {
                'diabetes': 'diabetic-friendly recipes',
                'low_oil': 'low-oil cooking',
                'low_salt': 'low-sodium recipes',
                'high_protein': 'high-protein dishes',
                'low_carb': 'low-carb options',
                'heart_healthy': 'heart-healthy cooking'
            }
            mods = [health_text.get(h, h) for h in profile.health_modifications]
            parts.append(f"Prefers {', '.join(mods)}.")

        # Cooking time preference
        if profile.time_available_weekday:
            if profile.time_available_weekday <= 20:
                parts.append('Needs quick recipes under 20 minutes.')
            elif profile.time_available_weekday <= 30:
                parts.append('Prefers recipes that take 20-30 minutes.')
            elif profile.time_available_weekday <= 45:
                parts.append('Has 30-45 minutes for cooking.')
            else:
                parts.append('Has time for elaborate cooking, 45+ minutes okay.')

        # Excluded ingredients (strong dislikes)
        if profile.specific_prohibitions:
            excluded = [p.replace('_', ' ') for p in profile.specific_prohibitions]
            parts.append(f"Does not like: {', '.join(excluded)}.")

        # Skill level
        if profile.skill_level:
            skill_text = {
                'beginner': 'Beginner cook, prefers simple recipes.',
                'intermediate': 'Intermediate cooking skills.',
                'advanced': 'Advanced cook, can handle complex recipes.'
            }
            if profile.skill_level in skill_text:
                parts.append(skill_text[profile.skill_level])

        # Household context
        if profile.household_type:
            if 'family' in profile.household_type or profile.multigenerational_household:
                parts.append('Cooking for family, needs crowd-pleasing recipes.')

        # Experimentation level
        if profile.experimentation_level:
            exp_text = {
                'stick_to_familiar': 'Prefers familiar, traditional recipes.',
                'open_within_comfort': 'Open to trying new recipes within comfort zone.',
                'love_experimenting': 'Loves experimenting with new cuisines and fusion.'
            }
            if profile.experimentation_level in exp_text:
                parts.append(exp_text[profile.experimentation_level])

        return ' '.join(parts)

    def _cache_embedding(self, user_id: str, embedding: List[float], profile_text: str):
        """
        Cache user taste embedding in Qdrant for faster future lookups.
        """
        try:
            from qdrant_client.models import PointStruct, VectorParams, Distance

            # Ensure collection exists
            try:
                self.qdrant.client.get_collection("user_taste_embeddings")
            except Exception:
                # Collection doesn't exist, create it
                self.qdrant.client.create_collection(
                    collection_name="user_taste_embeddings",
                    vectors_config=VectorParams(
                        size=768,  # Gemini embedding dimension
                        distance=Distance.COSINE
                    )
                )
                print("Created user_taste_embeddings collection")

            # Delete existing embedding for this user (if any)
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            self.qdrant.client.delete(
                collection_name="user_taste_embeddings",
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                )
            )

            # Insert new embedding
            self.qdrant.client.upsert(
                collection_name="user_taste_embeddings",
                points=[
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={
                            "user_id": user_id,
                            "profile_text": profile_text[:1000],  # Truncate for storage
                            "cached_at": datetime.utcnow().isoformat()
                        }
                    )
                ]
            )

        except Exception as e:
            # Caching failure is not critical
            print(f"Warning: Could not cache user embedding: {e}")

    def invalidate_cache(self, user_id: str):
        """
        Invalidate cached embedding for a user.
        Should be called when user profile is updated.
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            self.qdrant.client.delete(
                collection_name="user_taste_embeddings",
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                )
            )
        except Exception as e:
            print(f"Warning: Could not invalidate cache: {e}")
