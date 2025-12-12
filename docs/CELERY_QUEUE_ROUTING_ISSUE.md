# Celery Queue Routing Issue - Root Cause Analysis

## Date: 2025-12-08

---

## 🔴 The Problem

**Symptoms:**
- Tasks dispatched via Celery stay in `PENDING` state forever
- `celery inspect active` shows no tasks running
- Workers appear healthy but don't process tasks

**Impact:** Cannot process recipes asynchronously via Celery

---

## 🔍 Root Cause

### Queue Routing Mismatch

**Configuration in `annapurna/celery_app.py:27-31`:**
```python
task_routes={
    'annapurna.tasks.scraping.*': {'queue': 'scraping'},
    'annapurna.tasks.processing.*': {'queue': 'processing'},
    'annapurna.tasks.maintenance.*': {'queue': 'maintenance'},
}
```

This configuration routes tasks to **specific queues**:
- `batch_process_recipes_task` → `processing` queue
- `scrape_website_task` → `scraping` queue
- `cleanup_old_logs` → `maintenance` queue

**Worker command in `docker-compose.yml:75`:**
```yaml
command: celery -A annapurna.celery_app worker --loglevel=info --concurrency=4
```

The worker starts **without specifying queues**, so it only listens to the **default `celery` queue**.

### The Flow (What Happens)

1. **Task dispatched:** `batch_process_recipes_task.delay(batch_size=5)`
2. **Celery routing:** Task routed to `processing` queue (per config)
3. **Redis:** Task message stored in `processing` queue
4. **Worker:** Only listening to `celery` queue ❌
5. **Result:** Task stuck in PENDING, never picked up

### Verification

```bash
# Worker's active queues
celery -A annapurna.celery_app inspect active_queues
# Output: Only listening to 'celery' queue

# Test: Send to default queue
celery_app.send_task('...', queue='celery')
# Result: ✅ SUCCESS in 5 seconds!
```

---

## ✅ Solutions

### Option 1: Fix Worker Command (RECOMMENDED)

Update the worker to listen to all queues defined in routing config.

**File:** `docker-compose.yml:75`

**Before:**
```yaml
command: celery -A annapurna.celery_app worker --loglevel=info --concurrency=4
```

**After:**
```yaml
command: celery -A annapurna.celery_app worker -Q processing,scraping,maintenance,celery --loglevel=info --concurrency=4
```

**Explanation:**
- `-Q processing,scraping,maintenance,celery` tells worker to listen to all these queues
- Tasks will be processed from their respective queues
- Maintains separation of concerns (scraping vs processing vs maintenance)

**Benefits:**
- ✅ Proper queue isolation
- ✅ Can scale workers per queue type
- ✅ Better monitoring and debugging

**Apply:**
```bash
# Edit docker-compose.yml
# Then restart worker
docker-compose restart celery-worker

# Verify
docker exec annapurna-celery-worker celery -A annapurna.celery_app inspect active_queues
# Should show: processing, scraping, maintenance, celery
```

---

### Option 2: Remove Task Routing (SIMPLER)

Remove queue routing so all tasks use default queue.

**File:** `annapurna/celery_app.py:27-31`

**Before:**
```python
task_routes={
    'annapurna.tasks.scraping.*': {'queue': 'scraping'},
    'annapurna.tasks.processing.*': {'queue': 'processing'},
    'annapurna.tasks.maintenance.*': {'queue': 'maintenance'},
}
```

**After:**
```python
# Comment out or remove task routing
# task_routes={
#     'annapurna.tasks.scraping.*': {'queue': 'scraping'},
#     'annapurna.tasks.processing.*': {'queue': 'processing'},
#     'annapurna.tasks.maintenance.*': {'queue': 'maintenance'},
# }
```

**Benefits:**
- ✅ Simpler configuration
- ✅ No need to change docker-compose
- ✅ All tasks work immediately

**Drawbacks:**
- ❌ No queue separation
- ❌ Can't scale different task types independently
- ❌ Harder to debug (all tasks mixed together)

**Apply:**
```bash
# Edit annapurna/celery_app.py
# Restart worker
docker-compose restart celery-worker
```

---

### Option 3: Override Queue When Dispatching (WORKAROUND)

Send tasks to `celery` queue explicitly, bypassing routing.

**Example:**
```python
# Instead of:
batch_process_recipes_task.delay(batch_size=5)

# Use:
from annapurna.celery_app import celery_app
celery_app.send_task(
    'annapurna.tasks.processing.batch_process_recipes',
    kwargs={'batch_size': 5},
    queue='celery'  # Override routing
)
```

**Benefits:**
- ✅ Works immediately (no config changes)
- ✅ Can choose queue per task

**Drawbacks:**
- ❌ More verbose
- ❌ Easy to forget `queue='celery'`
- ❌ Not a permanent fix

---

## 📊 Testing Results

### Before Fix
```python
result = batch_process_recipes_task.delay(batch_size=5)
# State: PENDING (forever)
# Worker logs: (empty - no tasks picked up)
```

### After Fix (with queue='celery')
```python
result = celery_app.send_task('...', queue='celery')
# State: PENDING → SUCCESS (5 seconds)
# Result: {'status': 'completed', 'results': {'success': 0, 'failed': 2}}
```

---

## 🎯 Recommended Fix

**Use Option 1: Update Worker Command**

This is the proper solution that:
- Maintains architectural separation of queues
- Allows independent scaling
- Provides better monitoring

**Steps:**
1. Edit `docker-compose.yml` line 75
2. Add `-Q processing,scraping,maintenance,celery`
3. Restart worker: `docker-compose restart celery-worker`
4. Verify: `docker exec annapurna-celery-worker celery -A annapurna.celery_app inspect active_queues`

---

## 📝 Alternative: Multiple Workers Per Queue

For production, consider running dedicated workers per queue:

**docker-compose.yml:**
```yaml
celery-worker-processing:
  # ... same config ...
  command: celery -A annapurna.celery_app worker -Q processing --loglevel=info --concurrency=4

celery-worker-scraping:
  # ... same config ...
  command: celery -A annapurna.celery_app worker -Q scraping --loglevel=info --concurrency=2

celery-worker-maintenance:
  # ... same config ...
  command: celery -A annapurna.celery_app worker -Q maintenance --loglevel=info --concurrency=1
```

**Benefits:**
- Independent scaling per task type
- Scraping tasks won't block processing tasks
- Better resource allocation

---

## 🔧 Quick Fix Command

```bash
# Stop current worker
docker-compose stop celery-worker

# Edit docker-compose.yml line 75, change to:
# command: celery -A annapurna.celery_app worker -Q processing,scraping,maintenance,celery --loglevel=info --concurrency=4

# Start worker
docker-compose up -d celery-worker

# Verify it's listening to all queues
docker exec annapurna-celery-worker celery -A annapurna.celery_app inspect active_queues
```

---

## ✅ Status

- **Issue identified:** ✅ Queue routing mismatch
- **Root cause:** ✅ Worker not listening to routed queues
- **Workaround:** ✅ Send to 'celery' queue directly
- **Proper fix:** ⏳ Awaiting docker-compose.yml update

---

## 📚 Related Documentation

- Celery Routing: https://docs.celeryq.dev/en/stable/userguide/routing.html
- Queue Configuration: https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-task_routes
