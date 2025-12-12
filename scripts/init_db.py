#!/usr/bin/env python3
"""Initialize database schema for Project Annapurna"""

from annapurna.models.base import Base, engine
from annapurna.models import *  # Import all models to register them with Base

def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

    # Print created tables
    print("\nCreated tables:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")

if __name__ == "__main__":
    init_database()
