# Recipe PDF/Book Extraction Strategy

## Potential Sources

### 1. Tarla Dalal Books
- Tarla Dalal has 100+ published cookbooks
- Many available as PDFs online
- Average: 100-200 recipes per book
- **Potential**: 10,000+ recipes

### 2. Sanjeev Kapoor Books
- "Khazana of Indian Recipes" - 1000+ recipes
- Multiple other cookbooks
- **Potential**: 5,000+ recipes

### 3. Other Popular Authors
- Nisha Madhulika books
- Pankaj Bhadouria
- Chef Ranveer Brar
- Madhur Jaffrey

### 4. Public Domain Sources
- Government nutrition/cooking guides
- Educational recipe collections
- Archive.org cookbook collection

## Technical Approach

### PDF Text Extraction
```python
import PyPDF2
import pdfplumber
from pdf2image import convert_from_path
import pytesseract  # for OCR if needed
```

### Recipe Parsing Strategy
1. Extract raw text from PDF
2. Use LLM (Gemini) to:
   - Identify recipe boundaries
   - Extract recipe title, ingredients, instructions
   - Structure data into our schema
3. Store in database same as web-scraped recipes

### Quality Advantages
- ✅ High-quality, tested recipes
- ✅ Consistent formatting
- ✅ No web scraping failures
- ✅ Bulk processing (100s per book)
- ✅ Authoritative sources

## Legal Considerations
- Use only legally available PDFs
- Public domain works
- Creative Commons licensed
- Fair use for research/educational purposes

## Implementation Steps
1. Research available PDF sources
2. Create PDF extraction script
3. Test with sample PDFs
4. Batch process books
5. Store extracted recipes

## Estimated Yield
- 20 books × 200 recipes = 4,000 recipes
- 50 books × 100 recipes = 5,000 recipes
- **Total potential: 10,000-20,000 recipes**
