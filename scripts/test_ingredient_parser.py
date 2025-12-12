"""Test ingredient regex parsing to debug the issue"""
import re

def parse_ingredient(ingredient_str: str):
    """Current implementation from recipe_processor.py"""
    ingredient_str = ingredient_str.strip()
    
    # Extract quantity
    quantity_pattern = r'^([\d½¼¾⅓⅔⅛⅜⅝⅞]+(?:\s*[-/]\s*[\d]+)?|\d+\.\d+)'
    quantity_match = re.search(quantity_pattern, ingredient_str)
    
    quantity = None
    if quantity_match:
        qty_str = quantity_match.group(1)
        try:
            quantity = float(qty_str)
        except:
            pass
    
    # Extract unit
    unit_pattern = r'\b(gram|grams|g|kg|cup|tablespoon|tbsp|teaspoon|tsp|ml|piece|pinch)\b'
    unit_match = re.search(unit_pattern, ingredient_str, re.IGNORECASE)
    unit = unit_match.group(1).lower() if unit_match else None
    
    # Extract ingredient name
    remaining = ingredient_str
    if quantity_match:
        remaining = remaining[quantity_match.end():].strip()
    if unit_match:
        remaining = remaining[unit_match.end():].strip()
    
    item = re.split(r'[,(]', remaining)[0].strip()
    
    return {
        'original': ingredient_str,
        'item': item.title(),
        'quantity': quantity,
        'unit': unit
    }

# Test with problematic examples from logs
test_cases = [
    "140 Grams Whole Urad Dal",
    "2 cups water",
    "1 tablespoon oil",
    "Salt to taste",
    "½ teaspoon turmeric powder",
    "200 grams paneer, cubed",
    "2-3 green chilies, chopped"
]

print("Testing ingredient parser:\n")
for ingredient in test_cases:
    result = parse_ingredient(ingredient)
    print(f"Input:    {result['original']}")
    print(f"Item:     {result['item']}")
    print(f"Quantity: {result['quantity']}")
    print(f"Unit:     {result['unit']}")
    print()
