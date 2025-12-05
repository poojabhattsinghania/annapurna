"""Seed data for tag dimensions and master ingredients"""

import json

# Tag Dimensions Seed Data
TAG_DIMENSIONS = [
    # VIBE - Spice Level
    {
        "dimension_name": "vibe_spice",
        "dimension_category": "vibe",
        "data_type": "single_select",
        "allowed_values": [
            "spice_1_mild",
            "spice_2_gentle",
            "spice_3_standard",
            "spice_4_hot",
            "spice_5_fire"
        ],
        "is_required": True,
        "description": "Spice level from 1 (mild) to 5 (very spicy)"
    },

    # VIBE - Texture
    {
        "dimension_name": "vibe_texture",
        "dimension_category": "vibe",
        "data_type": "single_select",
        "allowed_values": [
            "texture_dry",
            "texture_semi_gravy",
            "texture_gravy",
            "texture_crispy",
            "texture_mashy",
            "texture_soupy"
        ],
        "is_required": True,
        "description": "Primary texture of the dish"
    },

    # VIBE - Flavor Profile
    {
        "dimension_name": "vibe_flavor",
        "dimension_category": "vibe",
        "data_type": "multi_select",
        "allowed_values": [
            "flavor_tangy",
            "flavor_creamy",
            "flavor_smoky",
            "flavor_earthy",
            "flavor_fermented",
            "flavor_sweet_savory",
            "flavor_umami"
        ],
        "is_required": False,
        "description": "Flavor characteristics (can select multiple)"
    },

    # VIBE - Complexity
    {
        "dimension_name": "vibe_complexity",
        "dimension_category": "vibe",
        "data_type": "single_select",
        "allowed_values": [
            "complex_instant",
            "complex_one_pot",
            "complex_elaborate",
            "complex_slow_cook"
        ],
        "is_required": True,
        "description": "Cooking complexity and time requirement"
    },

    # HEALTH - Dietary Type
    {
        "dimension_name": "health_diet_type",
        "dimension_category": "health",
        "data_type": "single_select",
        "allowed_values": [
            "diet_veg",
            "diet_vegan",
            "diet_eggetarian",
            "diet_nonveg"
        ],
        "is_required": True,
        "description": "Primary dietary classification"
    },

    # HEALTH - Jain Compatible
    {
        "dimension_name": "health_jain",
        "dimension_category": "health",
        "data_type": "boolean",
        "allowed_values": ["true", "false"],
        "is_required": False,
        "description": "No onion, garlic, or root vegetables"
    },

    # HEALTH - Vrat/Fasting Compatible
    {
        "dimension_name": "health_vrat",
        "dimension_category": "health",
        "data_type": "boolean",
        "allowed_values": ["true", "false"],
        "is_required": False,
        "description": "Suitable for religious fasting (farali)"
    },

    # HEALTH - Diabetic Friendly
    {
        "dimension_name": "health_diabetic_friendly",
        "dimension_category": "health",
        "data_type": "boolean",
        "allowed_values": ["true", "false"],
        "is_required": False,
        "description": "Low GI or suitable for diabetic diet"
    },

    # HEALTH - High Protein
    {
        "dimension_name": "health_high_protein",
        "dimension_category": "health",
        "data_type": "boolean",
        "allowed_values": ["true", "false"],
        "is_required": False,
        "description": "Protein > 15g per serving"
    },

    # HEALTH - Low Carb
    {
        "dimension_name": "health_low_carb",
        "dimension_category": "health",
        "data_type": "boolean",
        "allowed_values": ["true", "false"],
        "is_required": False,
        "description": "Carbs < 20g per serving"
    },

    # HEALTH - Gluten Free
    {
        "dimension_name": "health_gluten_free",
        "dimension_category": "health",
        "data_type": "boolean",
        "allowed_values": ["true", "false"],
        "is_required": False,
        "description": "No wheat, maida, or gluten-containing grains"
    },

    # CONTEXT - Meal Slot
    {
        "dimension_name": "context_meal_slot",
        "dimension_category": "context",
        "data_type": "multi_select",
        "allowed_values": [
            "meal_breakfast",
            "meal_tiffin",
            "meal_weeknight_dinner",
            "meal_sunday_feast",
            "meal_tea_time"
        ],
        "is_required": True,
        "description": "When this dish is typically consumed"
    },

    # CONTEXT - Demographic
    {
        "dimension_name": "context_demographic",
        "dimension_category": "context",
        "data_type": "multi_select",
        "allowed_values": [
            "demo_kid_friendly",
            "demo_geriatric",
            "demo_bachelor",
            "demo_party"
        ],
        "is_required": False,
        "description": "Target demographic suitability"
    },

    # CONTEXT - Regional Origin
    {
        "dimension_name": "context_region",
        "dimension_category": "context",
        "data_type": "single_select",
        "allowed_values": [
            "region_north_punjabi",
            "region_north_up",
            "region_north_rajasthan",
            "region_south_tamil",
            "region_south_kerala",
            "region_south_karnataka",
            "region_south_andhra",
            "region_west_gujarat",
            "region_west_maharashtra",
            "region_east_bengal",
            "region_east_northeast",
            "region_fusion"
        ],
        "is_required": True,
        "description": "Regional cuisine origin"
    }
]

# Common Ingredients Master Data (subset)
INGREDIENTS_MASTER = [
    # Vegetables
    {
        "standard_name": "Potato",
        "hindi_name": "Aloo",
        "search_synonyms": ["Batata", "Urulai", "Alu"],
        "category": "vegetable",
        "is_root_vegetable": True,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 78,
        "carbs_per_100g": 17.0,
        "protein_per_100g": 2.0,
        "calories_per_100g": 77.0
    },
    {
        "standard_name": "Onion",
        "hindi_name": "Pyaz",
        "search_synonyms": ["Kanda", "Eerulli", "Vengayam"],
        "category": "vegetable",
        "is_root_vegetable": True,
        "is_allium": True,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 10,
        "carbs_per_100g": 9.3,
        "protein_per_100g": 1.1,
        "calories_per_100g": 40.0
    },
    {
        "standard_name": "Garlic",
        "hindi_name": "Lahsun",
        "search_synonyms": ["Vellulli", "Poondu"],
        "category": "vegetable",
        "is_root_vegetable": True,
        "is_allium": True,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 30,
        "carbs_per_100g": 33.0,
        "protein_per_100g": 6.4,
        "calories_per_100g": 149.0
    },
    {
        "standard_name": "Tomato",
        "hindi_name": "Tamatar",
        "search_synonyms": ["Thakkali"],
        "category": "vegetable",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 15,
        "carbs_per_100g": 3.9,
        "protein_per_100g": 0.9,
        "calories_per_100g": 18.0
    },
    {
        "standard_name": "Cauliflower",
        "hindi_name": "Phool Gobi",
        "search_synonyms": ["Gobhi"],
        "category": "vegetable",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 15,
        "carbs_per_100g": 5.0,
        "protein_per_100g": 1.9,
        "calories_per_100g": 25.0
    },
    {
        "standard_name": "Spinach",
        "hindi_name": "Palak",
        "search_synonyms": ["Keerai"],
        "category": "vegetable",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 15,
        "carbs_per_100g": 3.6,
        "protein_per_100g": 2.9,
        "calories_per_100g": 23.0
    },

    # Legumes
    {
        "standard_name": "Chickpeas",
        "hindi_name": "Chole",
        "search_synonyms": ["Chana", "Kabuli Chana", "Garbanzo"],
        "category": "legume",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 28,
        "carbs_per_100g": 61.0,
        "protein_per_100g": 19.0,
        "calories_per_100g": 364.0
    },
    {
        "standard_name": "Red Lentils",
        "hindi_name": "Masoor Dal",
        "search_synonyms": ["Masur Dal"],
        "category": "legume",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 26,
        "carbs_per_100g": 63.0,
        "protein_per_100g": 26.0,
        "calories_per_100g": 353.0
    },

    # Grains
    {
        "standard_name": "Rice",
        "hindi_name": "Chawal",
        "search_synonyms": ["Arisi", "Bhat"],
        "category": "grain",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 73,
        "carbs_per_100g": 28.0,
        "protein_per_100g": 2.7,
        "calories_per_100g": 130.0
    },
    {
        "standard_name": "Wheat Flour",
        "hindi_name": "Atta",
        "search_synonyms": ["Gehun ka Atta", "Whole Wheat Flour"],
        "category": "grain",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 69,
        "carbs_per_100g": 72.0,
        "protein_per_100g": 13.0,
        "calories_per_100g": 364.0
    },
    {
        "standard_name": "Buckwheat Flour",
        "hindi_name": "Kuttu Ka Atta",
        "search_synonyms": ["Kuttu"],
        "category": "grain",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": True,
        "is_non_veg": False,
        "glycemic_index": 54,
        "carbs_per_100g": 71.5,
        "protein_per_100g": 13.3,
        "calories_per_100g": 343.0
    },

    # Dairy
    {
        "standard_name": "Paneer",
        "hindi_name": "Paneer",
        "search_synonyms": ["Indian Cottage Cheese"],
        "category": "dairy",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": True,
        "is_non_veg": False,
        "glycemic_index": 0,
        "carbs_per_100g": 1.2,
        "protein_per_100g": 18.0,
        "calories_per_100g": 265.0
    },
    {
        "standard_name": "Yogurt",
        "hindi_name": "Dahi",
        "search_synonyms": ["Curd", "Thayir"],
        "category": "dairy",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": True,
        "is_non_veg": False,
        "glycemic_index": 36,
        "carbs_per_100g": 4.7,
        "protein_per_100g": 3.5,
        "calories_per_100g": 61.0
    },

    # Spices
    {
        "standard_name": "Cumin",
        "hindi_name": "Jeera",
        "search_synonyms": ["Jeeragam", "Jire"],
        "category": "spice",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": True,
        "is_non_veg": False,
        "glycemic_index": 0,
        "carbs_per_100g": 44.2,
        "protein_per_100g": 17.8,
        "calories_per_100g": 375.0
    },
    {
        "standard_name": "Turmeric",
        "hindi_name": "Haldi",
        "search_synonyms": ["Manjal"],
        "category": "spice",
        "is_root_vegetable": True,
        "is_allium": False,
        "is_vrat_allowed": True,
        "is_non_veg": False,
        "glycemic_index": 0,
        "carbs_per_100g": 65.0,
        "protein_per_100g": 8.0,
        "calories_per_100g": 312.0
    },
    {
        "standard_name": "Coriander Powder",
        "hindi_name": "Dhania Powder",
        "search_synonyms": ["Kothamalli Powder"],
        "category": "spice",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": True,
        "is_non_veg": False,
        "glycemic_index": 0,
        "carbs_per_100g": 55.0,
        "protein_per_100g": 12.4,
        "calories_per_100g": 298.0
    },

    # Oils
    {
        "standard_name": "Mustard Oil",
        "hindi_name": "Sarson Ka Tel",
        "search_synonyms": ["Kadugu Ennai"],
        "category": "oil",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": True,
        "is_non_veg": False,
        "glycemic_index": 0,
        "carbs_per_100g": 0.0,
        "protein_per_100g": 0.0,
        "fat_per_100g": 100.0,
        "calories_per_100g": 884.0
    },
    {
        "standard_name": "Ghee",
        "hindi_name": "Ghee",
        "search_synonyms": ["Clarified Butter", "Nei"],
        "category": "oil",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": True,
        "is_non_veg": False,
        "glycemic_index": 0,
        "carbs_per_100g": 0.0,
        "protein_per_100g": 0.0,
        "fat_per_100g": 99.5,
        "calories_per_100g": 876.0
    },

    # For Jain recipes
    {
        "standard_name": "Ginger",
        "hindi_name": "Adrak",
        "search_synonyms": ["Inji", "Allam"],
        "category": "spice",
        "is_root_vegetable": True,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 15,
        "carbs_per_100g": 17.8,
        "protein_per_100g": 1.8,
        "calories_per_100g": 80.0
    },
    {
        "standard_name": "Carrot",
        "hindi_name": "Gajar",
        "search_synonyms": ["Carrot", "Gezer"],
        "category": "vegetable",
        "is_root_vegetable": True,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 39,
        "carbs_per_100g": 9.6,
        "protein_per_100g": 0.9,
        "calories_per_100g": 41.0
    },
    {
        "standard_name": "Green Beans",
        "hindi_name": "Phali",
        "search_synonyms": ["French Beans", "Beans"],
        "category": "vegetable",
        "is_root_vegetable": False,
        "is_allium": False,
        "is_vrat_allowed": False,
        "is_non_veg": False,
        "glycemic_index": 15,
        "carbs_per_100g": 7.0,
        "protein_per_100g": 1.8,
        "calories_per_100g": 31.0
    }
]

# Content Creators Seed Data
CONTENT_CREATORS = [
    {
        "name": "Nisha Madhulika",
        "platform": "youtube",
        "base_url": "https://www.youtube.com/@NishaMadhulika",
        "language": ["Hindi", "English"],
        "specialization": ["North Indian", "Daily Meals", "Traditional"]
    },
    {
        "name": "Hebbars Kitchen",
        "platform": "youtube",
        "base_url": "https://www.youtube.com/@HebbarsKitchen",
        "language": ["English", "Hindi"],
        "specialization": ["Pan-Indian", "South Indian", "North Indian"]
    },
    {
        "name": "Cook With Parul",
        "platform": "youtube",
        "base_url": "https://www.youtube.com/@CookWithParul",
        "language": ["Hindi", "Gujarati"],
        "specialization": ["Gujarati", "Jain", "Vrat"]
    },
    {
        "name": "Ranveer Brar",
        "platform": "youtube",
        "base_url": "https://www.youtube.com/@RanveerBrar",
        "language": ["Hindi", "English"],
        "specialization": ["Traditional", "Restaurant Style", "North Indian"]
    },
    {
        "name": "Tarla Dalal",
        "platform": "website",
        "base_url": "https://www.tarladalal.com",
        "language": ["English", "Hindi"],
        "specialization": ["Health", "Jain", "Diabetic", "Pan-Indian"]
    },
    {
        "name": "Jain Rasoi",
        "platform": "youtube",
        "base_url": "https://www.youtube.com/@JainRasoi",
        "language": ["Hindi"],
        "specialization": ["Jain", "Sattvic"]
    }
]

# Content Categories Seed Data
CONTENT_CATEGORIES = [
    {"category_name": "Indian Food", "parent_category_id": None, "scraping_priority": 1},
    {"category_name": "North Indian", "parent_name": "Indian Food", "scraping_priority": 1},
    {"category_name": "South Indian", "parent_name": "Indian Food", "scraping_priority": 2},
    {"category_name": "East Indian", "parent_name": "Indian Food", "scraping_priority": 3},
    {"category_name": "West Indian", "parent_name": "Indian Food", "scraping_priority": 2},
    {"category_name": "Dietary Specialized", "parent_name": "Indian Food", "scraping_priority": 2},
    {"category_name": "Jain Food", "parent_name": "Dietary Specialized", "scraping_priority": 2},
    {"category_name": "Vrat Food", "parent_name": "Dietary Specialized", "scraping_priority": 2},
    {"category_name": "Health Food", "parent_name": "Dietary Specialized", "scraping_priority": 3},
    {"category_name": "Breakfast", "parent_name": "Indian Food", "scraping_priority": 1},
    {"category_name": "Snacks", "parent_name": "Indian Food", "scraping_priority": 2},
]
