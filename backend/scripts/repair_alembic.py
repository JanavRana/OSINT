#!/usr/bin/env python3
"""
Repair script for Alembic migration state.

This script repairs a database that was initialized with Base.metadata.create_all()
instead of Alembic migrations. It:
1. Creates the alembic_version table if missing
2. Stamps the database at the correct migration version
3. Allows 'alembic upgrade head' to complete successfully

Usage:
    python scripts/repair_alembic.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect, text
from app.core.config import get_settings


def main():
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_database_url)
    inspector = inspect(engine)
    
    print("=" * 60)
    print("Alembic Migration Repair Script")
    print("=" * 60)
    
    # Check current state
    tables = inspector.get_table_names()
    print(f"\nExisting tables: {', '.join(tables)}")
    
    has_alembic = 'alembic_version' in tables
    has_users = 'users' in tables
    has_normalized_facts = 'normalized_facts' in tables
    has_investigations = 'investigations' in tables
    
    if has_investigations:
        investigations_columns = [col['name'] for col in inspector.get_columns('investigations')]
        has_user_id = 'user_id' in investigations_columns
    else:
        has_user_id = False
    
    print(f"\nCurrent state:")
    print(f"  ✓ investigations table: {'EXISTS' if has_investigations else 'MISSING'}")
    print(f"  ✓ normalized_facts table: {'EXISTS' if has_normalized_facts else 'MISSING'}")
    print(f"  ✓ users table: {'EXISTS' if has_users else 'MISSING'}")
    print(f"  ✓ investigations.user_id column: {'EXISTS' if has_user_id else 'MISSING'}")
    print(f"  ✓ alembic_version table: {'EXISTS' if has_alembic else 'MISSING'}")
    
    if not has_investigations:
        print("\n❌ ERROR: investigations table doesn't exist!")
        print("This script is for repairing partially migrated databases.")
        print("For a fresh database, run: alembic upgrade head")
        sys.exit(1)
    
    # Determine repair action
    if has_alembic:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()
            print(f"\n✓ alembic_version already exists with version: {current_version}")
            
            if not has_user_id:
                print("\n⚠️  investigations.user_id is missing but alembic_version exists.")
                print("Run: alembic upgrade head")
            else:
                print("\n✓ Database appears to be fully migrated!")
        return
    
    # Create alembic_version and stamp at appropriate version
    print("\n" + "=" * 60)
    print("Repairing alembic_version table...")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Create alembic_version table
        conn.execute(text(
            "CREATE TABLE alembic_version ("
            "  version_num VARCHAR(32) NOT NULL, "
            "  CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
            ")"
        ))
        print("\n✓ Created alembic_version table")
        
        # Determine which version to stamp at
        if has_users and has_user_id:
            # All migrations have been applied (via create_all())
            stamp_version = 'a1b2c3d4e5f6'
            print(f"✓ Database is fully initialized, stamping at: {stamp_version} (latest)")
        elif has_normalized_facts:
            # Only first migration has been applied
            stamp_version = '708401118290'
            print(f"✓ Database is partially initialized, stamping at: {stamp_version} (base)")
        else:
            # Edge case: investigations exists but normalized_facts doesn't
            stamp_version = '708401118290'
            print(f"✓ Stamping at base migration: {stamp_version}")
        
        conn.execute(text(
            f"INSERT INTO alembic_version (version_num) VALUES ('{stamp_version}')"
        ))
        conn.commit()
        print(f"✓ Stamped database at version: {stamp_version}")
    
    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)
    print("\n1. Run: alembic upgrade head")
    print("   This will apply any remaining migrations safely.\n")
    print("2. Verify the fix by checking for investigations.user_id:")
    print("   SELECT column_name FROM information_schema.columns")
    print("   WHERE table_name='investigations' AND column_name='user_id';\n")
    print("3. Restart your backend application.\n")
    print("✓ Repair complete!")


if __name__ == "__main__":
    main()
