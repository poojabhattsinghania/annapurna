"""Database health check script"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from annapurna.config import settings
import psycopg2

try:
    print("=" * 70)
    print("DATABASE HEALTH CHECK")
    print("=" * 70)

    print("\n🔌 Connecting to database...")
    print(f"   Host: {settings.database_url.split('@')[1].split('/')[0]}")

    conn = psycopg2.connect(settings.database_url, connect_timeout=10)
    cursor = conn.cursor()

    # Test query
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    print(f"✓ Database connected")
    print(f"   Version: {version[:80]}...")

    # Check connections
    cursor.execute("SELECT count(*) FROM pg_stat_activity")
    conn_count = cursor.fetchone()[0]

    cursor.execute("SHOW max_connections")
    max_conn = cursor.fetchone()[0]

    print(f"\n📊 Connection Stats:")
    print(f"   Active: {conn_count}/{max_conn}")

    # Check long-running queries
    cursor.execute("""
        SELECT count(*)
        FROM pg_stat_activity
        WHERE state != 'idle'
        AND query_start < NOW() - INTERVAL '5 minutes'
    """)
    long_running = cursor.fetchone()[0]

    if long_running > 0:
        print(f"   ⚠️  Long-running queries: {long_running}")
    else:
        print(f"   ✓ No long-running queries")

    # Check table exists
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'recipes')")
    recipes_exists = cursor.fetchone()[0]
    print(f"\n📁 Tables:")
    print(f"   Recipes table: {'✓ EXISTS' if recipes_exists else '✗ MISSING'}")

    if recipes_exists:
        # Check recipe count
        cursor.execute("SELECT count(*) FROM recipes")
        recipe_count = cursor.fetchone()[0]
        print(f"   Recipe count: {recipe_count:,}")

        # Check for images (existing field from recipe-scrapers)
        cursor.execute("""
            SELECT count(*)
            FROM recipes
            WHERE description IS NOT NULL
        """)
        with_desc = cursor.fetchone()[0]
        print(f"   With descriptions: {with_desc:,} ({with_desc*100//recipe_count if recipe_count > 0 else 0}%)")

    # Check if migration needed
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'recipes'
        AND column_name IN ('primary_image_url', 'thumbnail_url', 'youtube_video_id')
        ORDER BY column_name
    """)

    migrated_columns = [row[0] for row in cursor.fetchall()]
    migration_done = len(migrated_columns) == 3

    print(f"\n🔄 Migration Status:")
    if migration_done:
        print(f"   ✅ COMPLETED - All image columns exist")
        print(f"   Columns: {', '.join(migrated_columns)}")
    else:
        print(f"   ⏳ PENDING - Migration needed")
        if migrated_columns:
            print(f"   Partial columns: {', '.join(migrated_columns)}")
        print(f"   Missing: primary_image_url, thumbnail_url, youtube_video_id")

    # Check recipe_media table
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'recipe_media')")
    media_table_exists = cursor.fetchone()[0]

    if media_table_exists:
        cursor.execute("SELECT count(*) FROM recipe_media")
        media_count = cursor.fetchone()[0]
        print(f"   Recipe media table: ✓ EXISTS ({media_count:,} entries)")
    else:
        print(f"   Recipe media table: ⏳ PENDING")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("✅ DATABASE IS HEALTHY!")
    print("=" * 70)

    if not migration_done:
        print("\nNext step: Run migration")
        print("   docker exec annapurna-api alembic upgrade head")
    else:
        print("\n✓ Ready to scrape recipes with image extraction!")

    sys.exit(0)

except psycopg2.OperationalError as e:
    print(f"\n❌ CONNECTION FAILED")
    print(f"   Error: {e}")
    print("\n" + "=" * 70)
    print("TROUBLESHOOTING STEPS:")
    print("=" * 70)
    print("1. Check AWS RDS instance status in AWS Console")
    print("2. Verify security group allows port 5432 from your IP/VPC")
    print("3. Check VPC/subnet configuration")
    print("4. Try rebooting the RDS instance if it's stuck")
    print("5. Check for maintenance windows or AWS regional issues")
    print("\nAWS RDS Console:")
    print("https://console.aws.amazon.com/rds/")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
