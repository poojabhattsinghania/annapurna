#!/bin/bash
docker exec annapurna-celery-worker python3 <<'EOFPY'
import sys
sys.path.insert(0, '/app')

from annapurna.database.session import get_db  
from annapurna.database.models import RawScrapedContent
from annapurna.tasks.processing import batch_process_recipes
from sqlalchemy import func

# Get counts
db = next(get_db())
total = db.query(func.count(RawScrapedContent.id)).scalar()
unprocessed = db.query(func.count(RawScrapedContent.id)).filter(
    RawScrapedContent.processed == False
).scalar()

print(f'✓ Qdrant: http://13.200.235.39:6333')
print(f'✓ Total recipes: {total}')  
print(f'✓ Unprocessed: {unprocessed}')

# Queue batch processing - process ALL recipes
if unprocessed > 0:
    print(f'\nQueueing {unprocessed} recipes for processing...')
    result = batch_process_recipes.delay(batch_size=unprocessed)
    print(f'✓ Task queued: {result.task_id}')
    print(f'\nMonitor with: docker logs -f annapurna-celery-worker')
else:
    print('\nNo recipes to process!')
EOFPY
