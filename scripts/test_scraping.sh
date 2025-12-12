#!/bin/bash

# Test scraping 5 recipes from vegrecipesofindia
echo "Testing scraping 5 recipes from vegrecipesofindia..."
echo

urls=(
  "https://www.vegrecipesofindia.com/aloo-gobi-recipe/"
  "https://www.vegrecipesofindia.com/dal-makhani-restaurant-style/"
  "https://www.vegrecipesofindia.com/paneer-butter-masala/"
  "https://www.vegrecipesofindia.com/pav-bhaji-recipe/"
  "https://www.vegrecipesofindia.com/rajma-masala-recipe/"
)

for url in "${urls[@]}"; do
  echo "Scraping: $url"
  result=$(curl -s -X POST "http://localhost:8000/v1/scrape/website" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$url\", \"creator_name\": \"Indian Healthy Recipes\"}")

  message=$(echo "$result" | jq -r '.message')
  success=$(echo "$result" | jq -r '.success')

  if [ "$success" = "true" ]; then
    echo "  ✓ $message"
  else
    echo "  ✗ $message"
  fi

  echo
  sleep 3  # Rate limiting
done

echo "Done!"
