"""Test the FIXED ingredient regex parsing"""
import re

def parse_ingredient_fixed(ingredient_str: str):
    """FIXED implementation"""
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
    
    # Extract unit pattern
    unit_pattern = r'\b(gram|grams|g|kg|cup|cups|tablespoon|tablespoons|tbsp|teaspoon|teaspoons|tsp|ml|piece|pinch|whole)\b'
    unit_match = re.search(unit_pattern, ingredient_str, re.IGNORECASE)
    unit = unit_match.group(1).lower() if unit_match else None
    
    # Extract ingredient name - THE FIX
    remaining = ingredient_str
    if quantity_match:
        remaining = remaining[quantity_match.end():].strip()
    
    # THIS IS THE FIX: Remove unit from remaining string, not from original position
    if unit_match and unit:
        unit_in_remaining = re.search(unit_pattern, remaining, re.IGNORECASE)
        if unit_in_remaining:
            remaining = remaining[unit_in_remaining.end():].strip()
    
    item = re.split(r'[,(]', remaining)[0].strip()
    
    return {
        'original': ingredient_str,
        'item': item.title(),
        'quantity': quantity,
        'unit': unit
    }

# Test cases
test_cases = [
    "140 Grams Whole Urad Dal",
    "2 cups water",
    "1 tablespoon oil",
    "Salt to taste",
    "½ teaspoon turmeric powder",
    "200 grams paneer, cubed",
    "2-3 green chilies, chopped"
]

print("Testing FIXED ingredient parser:\n")
for ingredient in test_cases:
    result = parse_ingredient_fixed(ingredient)
    status = "✓" if result['item'] and len(result['item']) > 2 else "✗"
    print(f"{status} Input:    {result['original']}")
    print(f"  Item:     {result['item']}")
    print(f"  Quantity: {result['quantity']}")
    print(f"  Unit:     {result['unit']}")
    print()
