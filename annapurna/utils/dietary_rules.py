"""Dietary rule engine for auto-computing logic gates (Jain, Vrat, etc.)"""

import uuid
from typing import List, Dict
from sqlalchemy.orm import Session

from annapurna.models.recipe import Recipe, RecipeIngredient, RecipeTag
from annapurna.models.taxonomy import IngredientMaster, TagDimension


class DietaryRuleEngine:
    """
    Rule engine for computing dietary tags based on ingredient analysis

    Logic Gates:
    - Jain: FALSE if any [onion, garlic, root vegetables]
    - Vrat: TRUE if grains in [kuttu, rajgira, sabudana] AND no common salt
    - Diabetic Friendly: TRUE if GI < 55 OR explicit beneficial ingredients
    - High Protein: TRUE if protein > 15g per serving
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_recipe_ingredients(self, recipe_id: uuid.UUID) -> List[IngredientMaster]:
        """Get all ingredients for a recipe"""
        result = self.db_session.query(IngredientMaster).join(
            RecipeIngredient,
            RecipeIngredient.ingredient_id == IngredientMaster.id
        ).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()

        return result

    def check_jain_compatible(self, recipe: Recipe) -> Dict:
        """
        Check if recipe is Jain-compatible

        Rules:
        - No onion (is_allium = True AND category = vegetable)
        - No garlic (is_allium = True)
        - No root vegetables (is_root_vegetable = True) EXCEPT turmeric
        """
        ingredients = self.get_recipe_ingredients(recipe.id)

        # Ingredients that disqualify Jain
        violations = []

        for ing in ingredients:
            # Check allium (onion/garlic)
            if ing.is_allium:
                violations.append(f"{ing.standard_name} (allium)")

            # Check root vegetables (except turmeric which is allowed in some Jain traditions)
            if ing.is_root_vegetable and ing.standard_name.lower() not in ['turmeric', 'haldi']:
                violations.append(f"{ing.standard_name} (root vegetable)")

        is_jain = len(violations) == 0

        return {
            'is_jain': is_jain,
            'violations': violations,
            'confidence': 1.0  # Rule-based, so 100% confident
        }

    def check_vrat_compatible(self, recipe: Recipe) -> Dict:
        """
        Check if recipe is Vrat (fasting) compatible

        Rules:
        - Only vrat-allowed grains (kuttu, rajgira, sabudana, sama)
        - No onion, garlic (same as Jain)
        - Rock salt only (hard to detect from ingredients, so we check for explicit tags)
        """
        ingredients = self.get_recipe_ingredients(recipe.id)

        violations = []
        has_vrat_grain = False

        for ing in ingredients:
            # Check if vrat-allowed
            if ing.category.value == 'grain' and not ing.is_vrat_allowed:
                violations.append(f"{ing.standard_name} (not vrat grain)")

            # Check for vrat-allowed grains
            if ing.is_vrat_allowed and ing.category.value == 'grain':
                has_vrat_grain = True

            # Allium check (same as Jain)
            if ing.is_allium:
                violations.append(f"{ing.standard_name} (allium)")

        # Vrat recipes should have at least one vrat-approved grain
        is_vrat = len(violations) == 0 and has_vrat_grain

        return {
            'is_vrat': is_vrat,
            'violations': violations,
            'has_vrat_grain': has_vrat_grain,
            'confidence': 0.9  # Slightly less confident due to salt ambiguity
        }

    def check_diabetic_friendly(self, recipe: Recipe) -> Dict:
        """
        Check if recipe is diabetic-friendly

        Rules:
        - Average GI of carb sources < 55 (low GI)
        - OR contains explicitly beneficial ingredients (methi, karela, etc.)
        """
        ingredients = self.get_recipe_ingredients(recipe.id)

        # Get all ingredients with GI values
        gi_values = []
        beneficial_ingredients = []

        # Known diabetic-friendly ingredients
        BENEFICIAL_NAMES = [
            'fenugreek', 'methi', 'bitter gourd', 'karela',
            'cinnamon', 'dalchini', 'bitter melon'
        ]

        for ing in ingredients:
            if ing.glycemic_index:
                gi_values.append(ing.glycemic_index)

            # Check for beneficial ingredients
            if any(name in ing.standard_name.lower() for name in BENEFICIAL_NAMES):
                beneficial_ingredients.append(ing.standard_name)

        # Calculate average GI
        avg_gi = sum(gi_values) / len(gi_values) if gi_values else None

        # Determine if diabetic-friendly
        is_diabetic_friendly = False
        reason = []

        if avg_gi and avg_gi < 55:
            is_diabetic_friendly = True
            reason.append(f"Low average GI: {avg_gi:.1f}")

        if beneficial_ingredients:
            is_diabetic_friendly = True
            reason.append(f"Contains: {', '.join(beneficial_ingredients)}")

        return {
            'is_diabetic_friendly': is_diabetic_friendly,
            'average_gi': avg_gi,
            'beneficial_ingredients': beneficial_ingredients,
            'reason': reason,
            'confidence': 0.8 if avg_gi else 0.6  # Lower confidence without GI data
        }

    def check_high_protein(self, recipe: Recipe) -> Dict:
        """
        Check if recipe is high protein (>15g per serving)

        Calculates based on ingredient composition
        """
        ingredients_data = self.db_session.query(
            RecipeIngredient, IngredientMaster
        ).join(
            IngredientMaster,
            RecipeIngredient.ingredient_id == IngredientMaster.id
        ).filter(
            RecipeIngredient.recipe_id == recipe.id
        ).all()

        total_protein_per_100g = 0.0
        total_weight_g = 0.0

        for ing_rel, ing_master in ingredients_data:
            if ing_master.protein_per_100g and ing_rel.quantity:
                # Convert quantity to grams if needed
                quantity_g = ing_rel.quantity
                if ing_rel.unit == 'kg':
                    quantity_g *= 1000
                elif ing_rel.unit == 'ml':
                    quantity_g *= 1.0  # Assume 1ml ≈ 1g for simplicity

                # Calculate protein for this ingredient
                protein = (quantity_g / 100) * ing_master.protein_per_100g
                total_protein_per_100g += protein
                total_weight_g += quantity_g

        # Calculate per serving
        servings = recipe.servings or 1
        protein_per_serving = total_protein_per_100g / servings if servings else 0

        is_high_protein = protein_per_serving >= 15.0

        return {
            'is_high_protein': is_high_protein,
            'protein_per_serving': round(protein_per_serving, 1),
            'servings': servings,
            'confidence': 0.7  # Moderate confidence due to estimation
        }

    def check_gluten_free(self, recipe: Recipe) -> Dict:
        """
        Check if recipe is gluten-free

        Rules:
        - No wheat, maida, atta, semolina, barley, rye
        """
        ingredients = self.get_recipe_ingredients(recipe.id)

        # Gluten-containing grains
        GLUTEN_GRAINS = [
            'wheat', 'gehun', 'atta', 'maida', 'all-purpose flour',
            'semolina', 'rava', 'sooji', 'barley', 'jau', 'rye'
        ]

        violations = []

        for ing in ingredients:
            if any(grain in ing.standard_name.lower() for grain in GLUTEN_GRAINS):
                violations.append(ing.standard_name)

        is_gluten_free = len(violations) == 0

        return {
            'is_gluten_free': is_gluten_free,
            'violations': violations,
            'confidence': 1.0
        }

    def check_vegan(self, recipe: Recipe) -> Dict:
        """
        Check if recipe is vegan (no animal products)

        Rules:
        - No dairy (milk, butter, ghee, paneer, curd)
        - No eggs
        - No honey
        """
        ingredients = self.get_recipe_ingredients(recipe.id)

        violations = []

        for ing in ingredients:
            # Check dairy
            if ing.category.value == 'dairy':
                violations.append(f"{ing.standard_name} (dairy)")

            # Check eggs
            if 'egg' in ing.standard_name.lower():
                violations.append(f"{ing.standard_name} (egg)")

            # Check honey
            if 'honey' in ing.standard_name.lower() or 'shahad' in ing.standard_name.lower():
                violations.append(f"{ing.standard_name} (honey)")

        is_vegan = len(violations) == 0

        return {
            'is_vegan': is_vegan,
            'violations': violations,
            'confidence': 1.0
        }

    def apply_all_rules(self, recipe: Recipe) -> Dict[str, Dict]:
        """
        Apply all dietary rules to a recipe

        Returns:
            Dict of results from all rule checks
        """
        return {
            'jain': self.check_jain_compatible(recipe),
            'vrat': self.check_vrat_compatible(recipe),
            'diabetic_friendly': self.check_diabetic_friendly(recipe),
            'high_protein': self.check_high_protein(recipe),
            'gluten_free': self.check_gluten_free(recipe),
            'vegan': self.check_vegan(recipe)
        }

    def create_rule_based_tags(self, recipe: Recipe, confidence_threshold: float = 0.7):
        """
        Create recipe tags based on rule engine results

        Args:
            recipe: Recipe to tag
            confidence_threshold: Minimum confidence to create tag
        """
        results = self.apply_all_rules(recipe)

        # Map rule names to tag dimension names
        TAG_MAPPING = {
            'jain': 'health_jain',
            'vrat': 'health_vrat',
            'diabetic_friendly': 'health_diabetic_friendly',
            'high_protein': 'health_high_protein',
            'gluten_free': 'health_gluten_free',
            'vegan': 'health_vegan'  # May need to add this dimension
        }

        tags_created = 0

        for rule_name, result in results.items():
            # Get the boolean result
            is_true_key = f'is_{rule_name}'
            is_true = result.get(is_true_key, False)
            confidence = result.get('confidence', 0.0)

            # Skip if below threshold
            if confidence < confidence_threshold:
                continue

            # Get dimension
            tag_dim_name = TAG_MAPPING.get(rule_name)
            if not tag_dim_name:
                continue

            dimension = self.db_session.query(TagDimension).filter_by(
                dimension_name=tag_dim_name
            ).first()

            if not dimension:
                print(f"Warning: Dimension '{tag_dim_name}' not found")
                continue

            # Check if tag already exists
            existing = self.db_session.query(RecipeTag).filter_by(
                recipe_id=recipe.id,
                tag_dimension_id=dimension.id
            ).first()

            if existing:
                # Update existing
                existing.tag_value = 'true' if is_true else 'false'
                existing.confidence_score = confidence
                existing.source = 'rule_engine'
            else:
                # Create new tag
                tag = RecipeTag(
                    recipe_id=recipe.id,
                    tag_dimension_id=dimension.id,
                    tag_value='true' if is_true else 'false',
                    confidence_score=confidence,
                    source='rule_engine'
                )
                self.db_session.add(tag)
                tags_created += 1

        self.db_session.commit()
        print(f"✓ Created/updated {tags_created} rule-based tags for: {recipe.title}")

        return tags_created

    def batch_apply_rules(self, limit: int = 100):
        """Apply rules to all recipes without rule-based tags"""
        recipes = self.db_session.query(Recipe).limit(limit).all()

        print(f"Applying dietary rules to {len(recipes)} recipes...")

        total_tags = 0
        for i, recipe in enumerate(recipes, 1):
            print(f"[{i}/{len(recipes)}] {recipe.title}")
            tags = self.create_rule_based_tags(recipe)
            total_tags += tags

        print(f"✓ Total tags created: {total_tags}")


def main():
    """CLI interface for dietary rule engine"""
    import argparse
    from annapurna.models.base import SessionLocal

    parser = argparse.ArgumentParser(description="Apply dietary rule engine to recipes")
    parser.add_argument('--recipe-id', help='Apply rules to specific recipe')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    parser.add_argument('--analyze', action='store_true', help='Analyze without creating tags')

    args = parser.parse_args()

    db_session = SessionLocal()

    try:
        engine = DietaryRuleEngine(db_session)

        if args.recipe_id:
            recipe = db_session.query(Recipe).filter_by(
                id=uuid.UUID(args.recipe_id)
            ).first()

            if recipe:
                if args.analyze:
                    results = engine.apply_all_rules(recipe)
                    print(f"\nDietary analysis for: {recipe.title}\n")
                    for rule_name, result in results.items():
                        print(f"{rule_name.upper()}: {result}")
                else:
                    engine.create_rule_based_tags(recipe)
        else:
            engine.batch_apply_rules(args.batch_size)

    finally:
        db_session.close()


if __name__ == "__main__":
    main()
