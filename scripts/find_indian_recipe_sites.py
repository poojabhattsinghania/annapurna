"""Find high-quality Indian recipe websites with schema.org data"""

POTENTIAL_SITES = [
    "https://www.indianhealthyrecipes.com",  # Swasthi's recipes
    "https://www.cookwithmanali.com",  # Popular Indian food blog
    "https://www.archanaskitchen.com",  # Large Indian recipe database
    "https://www.chefkunalkapur.com",  # Celebrity chef
    "https://www.tarladalal.com",  # Huge recipe collection
    "https://www.sanjeevkapoor.com",  # Famous chef
    "https://www.madhurasrecipe.com",  # Marathi recipes
    "https://www.yummytummyaarthi.com",  # South Indian focus
]

print("Recommended sites to scrape:")
for i, site in enumerate(POTENTIAL_SITES, 1):
    print(f"{i}. {site}")

print("\nChecking schema.org availability on top 3...")
