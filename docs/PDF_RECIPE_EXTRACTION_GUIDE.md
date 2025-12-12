# PDF Recipe Extraction Guide

## Setup

### 1. Install PDF Libraries

```bash
# Add to requirements.txt
echo "PyPDF2>=3.0.0" >> annapurna/requirements.txt
echo "pdfplumber>=0.10.0" >> annapurna/requirements.txt

# Rebuild Docker container
docker-compose build api

# OR install in running container
docker exec annapurna-api pip install PyPDF2 pdfplumber
```

### 2. Find Recipe Book PDFs

**Legal Sources:**
- Archive.org cookbook collection
- Open-source recipe compilations
- Public domain cookbooks
- Personal PDF collections

**Popular Indian Cookbook PDFs:**
- Tarla Dalal books (if legally available)
- Sanjeev Kapoor collections
- Government nutrition guides
- Regional recipe compilations

## Usage

### Extract Recipes from PDF

```bash
# Basic usage
docker exec annapurna-api python extract_recipes_from_pdf.py /path/to/book.pdf "Author Name"

# Example
docker exec annapurna-api python extract_recipes_from_pdf.py /data/tarla_dalal_cookbook.pdf "Tarla Dalal"
```

### Workflow

1. **Place PDF in accessible location:**
   ```bash
   cp your_cookbook.pdf ~/Desktop/KMKB/recipe_pdfs/
   ```

2. **Run extraction:**
   ```bash
   docker exec annapurna-api python extract_recipes_from_pdf.py \
     /app/recipe_pdfs/your_cookbook.pdf \
     "Author Name"
   ```

3. **Monitor extraction:**
   - Script shows progress (pages, chunks, recipes found)
   - Recipes saved to `raw_scraped_content` table
   - Source platform: `pdf_book`

4. **Process recipes:**
   - Recipes automatically queued for processing
   - LLM processes into structured format
   - Searchable via API

## How It Works

1. **PDF Text Extraction**
   - Uses PyPDF2 or pdfplumber
   - Extracts text from all pages
   - ~50-100 pages/minute

2. **Text Chunking**
   - Splits into 50KB chunks
   - Handles large books efficiently
   - Processes chunk by chunk

3. **LLM Recipe Parsing**
   - Gemini 2.0 Flash identifies recipes
   - Extracts structured data:
     - Title
     - Ingredients (with quantities)
     - Instructions (step-by-step)
     - Prep/cook time
     - Servings
   - Filters out non-recipe content

4. **Database Storage**
   - Stores as `RawScrapedContent`
   - Same format as web-scraped recipes
   - Automatic deduplication
   - Ready for processing pipeline

## Expected Yield

| Book Type | Pages | Recipes | Time |
|-----------|-------|---------|------|
| Small cookbook | 50 | 30-50 | 2-3 min |
| Medium cookbook | 150 | 100-150 | 5-10 min |
| Large collection | 300 | 200-300 | 10-20 min |
| Mega compilation | 1000 | 500-1000 | 30-60 min |

## Advantages Over Web Scraping

✅ **No rate limiting** - Process entire books at once
✅ **High quality** - Tested, authoritative recipes
✅ **Batch processing** - 100s of recipes per book
✅ **No website dependencies** - Works offline
✅ **Structured content** - Books have consistent format
✅ **No duplicates** - Books curated by editors

## Cost Estimate

- **LLM API cost:** ~$0.01-0.05 per book
- **Time:** 5-20 minutes per book
- **Yield:** 100-300 recipes per book

**For 50k recipes:**
- 200 books × 250 recipes = 50,000 recipes
- Cost: $2-10 for LLM API calls
- Time: 16-66 hours (can run parallel)

## Next Steps

1. Install PDF libraries
2. Find/acquire recipe book PDFs
3. Test with 1-2 sample books
4. Batch process collection
5. Monitor quality and adjust

## Sample Command Workflow

```bash
# 1. Install libraries
docker exec annapurna-api pip install PyPDF2 pdfplumber

# 2. Create PDF directory
mkdir -p ~/Desktop/KMKB/recipe_pdfs

# 3. Place PDFs
cp tarla_dalal_*.pdf ~/Desktop/KMKB/recipe_pdfs/

# 4. Process each PDF
for pdf in recipe_pdfs/*.pdf; do
    echo "Processing: $pdf"
    docker exec annapurna-api python extract_recipes_from_pdf.py \
        "/app/$(basename $pdf)" \
        "$(basename $pdf .pdf)"
done

# 5. Check results
docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent

db = SessionLocal()
pdf_count = db.query(RawScrapedContent).filter(
    RawScrapedContent.source_platform == 'pdf_book'
).count()
print(f'PDF recipes in database: {pdf_count:,}')
db.close()
"
```
