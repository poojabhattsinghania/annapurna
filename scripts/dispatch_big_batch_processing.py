#!/usr/bin/env python3
"""
Dispatch a big batch of recipe processing tasks
"""

from annapurna.celery_app import celery_app
from annapurna.tasks.processing import batch_process_recipes_task

def dispatch_big_batch(num_batches: int = 30, batch_size: int = 500):
    """
    Dispatch multiple large batches of recipe processing

    Args:
        num_batches: Number of batches to dispatch
        batch_size: Size of each batch
    """

    print(f"Dispatching {num_batches} batches of {batch_size} recipes each...")
    print(f"Total recipes to process: {num_batches * batch_size} = {num_batches * batch_size:,}")
    print()

    task_ids = []

    for i in range(num_batches):
        task = batch_process_recipes_task.apply_async(
            args=[batch_size],
            queue='processing'
        )
        task_ids.append(task.id)

        if (i + 1) % 10 == 0:
            print(f"Dispatched batch {i + 1}/{num_batches}")

    print()
    print(f"✅ Successfully dispatched {len(task_ids)} processing batches!")
    print()
    print("Task IDs:")
    for i, task_id in enumerate(task_ids[:5]):
        print(f"  {i + 1}. {task_id}")

    if len(task_ids) > 5:
        print(f"  ... and {len(task_ids) - 5} more")

    print()
    print("Monitor progress at: http://localhost:5555 (Flower)")

if __name__ == '__main__':
    # Dispatch 30 batches of 500 recipes = 15,000 total
    dispatch_big_batch(num_batches=30, batch_size=500)
