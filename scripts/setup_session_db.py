"""
Database migration script for session management tables

Run this to create the necessary session tables in PostgreSQL
"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from fiml.core.config import settings
from fiml.core.logging import get_logger
from fiml.sessions.db import CREATE_TABLES_SQL

logger = get_logger(__name__)


async def create_session_tables():
    """Create session management tables in PostgreSQL"""
    
    print("\n" + "=" * 70)
    print("FIML Session Management - Database Setup")
    print("=" * 70)
    
    print(f"\nConnecting to database...")
    print(f"Host: {settings.postgres_host}:{settings.postgres_port}")
    print(f"Database: {settings.postgres_db}")
    
    try:
        # Create async engine
        engine = create_async_engine(
            settings.database_url,
            echo=True,
        )
        
        async with engine.begin() as conn:
            print("\n[1] Creating sessions table...")
            
            # Split and execute each statement
            statements = CREATE_TABLES_SQL.strip().split(';')
            
            for i, statement in enumerate(statements, 1):
                statement = statement.strip()
                if statement:
                    print(f"\n  Executing statement {i}...")
                    await conn.execute(text(statement))
            
            print("\n✓ All tables created successfully!")
        
        await engine.dispose()
        
        print("\n" + "=" * 70)
        print("Database setup completed successfully!")
        print("=" * 70)
        print("\nCreated tables:")
        print("  • sessions")
        print("  • session_metrics")
        print("\nCreated indexes:")
        print("  • idx_sessions_user_id")
        print("  • idx_sessions_type")
        print("  • idx_sessions_created_at")
        print("  • idx_sessions_expires_at")
        print("  • idx_sessions_archived")
        print("  • idx_sessions_archived_at")
        print("  • idx_sessions_cleanup")
        print("  • idx_session_metrics_session_id")
        print("  • idx_session_metrics_user_id")
        print("  • idx_session_metrics_type")
        print("  • idx_session_metrics_created_at")
        
        print("\n✨ Session management system is ready to use!\n")
        
    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        logger.error(f"Database setup failed: {e}")
        raise


async def verify_tables():
    """Verify that session tables exist"""
    
    print("\n" + "=" * 70)
    print("Verifying Session Tables")
    print("=" * 70)
    
    try:
        engine = create_async_engine(settings.database_url, echo=False)
        
        async with engine.begin() as conn:
            # Check sessions table
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'sessions'"
            ))
            sessions_exists = result.scalar() > 0
            
            # Check session_metrics table
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'session_metrics'"
            ))
            metrics_exists = result.scalar() > 0
            
            print(f"\n  sessions table: {'✓ EXISTS' if sessions_exists else '✗ NOT FOUND'}")
            print(f"  session_metrics table: {'✓ EXISTS' if metrics_exists else '✗ NOT FOUND'}")
            
            if sessions_exists and metrics_exists:
                # Get row counts
                result = await conn.execute(text("SELECT COUNT(*) FROM sessions"))
                session_count = result.scalar()
                
                result = await conn.execute(text("SELECT COUNT(*) FROM session_metrics"))
                metrics_count = result.scalar()
                
                print(f"\n  Current sessions: {session_count}")
                print(f"  Current metrics: {metrics_count}")
                
                print("\n✓ All session tables verified!")
            else:
                print("\n⚠ Some tables missing - run create_session_tables() first")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"\n❌ Error verifying tables: {e}")
        logger.error(f"Table verification failed: {e}")


async def drop_session_tables():
    """Drop session tables (use with caution!)"""
    
    print("\n" + "=" * 70)
    print("⚠️  WARNING: Dropping Session Tables")
    print("=" * 70)
    
    confirmation = input("\nThis will DELETE all session data. Type 'DROP' to confirm: ")
    
    if confirmation != "DROP":
        print("\n✓ Operation cancelled")
        return
    
    try:
        engine = create_async_engine(settings.database_url, echo=True)
        
        async with engine.begin() as conn:
            print("\n[1] Dropping session_metrics table...")
            await conn.execute(text("DROP TABLE IF EXISTS session_metrics CASCADE"))
            
            print("\n[2] Dropping sessions table...")
            await conn.execute(text("DROP TABLE IF EXISTS sessions CASCADE"))
            
            print("\n✓ Tables dropped successfully!")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"\n❌ Error dropping tables: {e}")
        logger.error(f"Table drop failed: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            asyncio.run(create_session_tables())
        elif command == "verify":
            asyncio.run(verify_tables())
        elif command == "drop":
            asyncio.run(drop_session_tables())
        else:
            print(f"\nUnknown command: {command}")
            print("\nUsage:")
            print("  python -m scripts.setup_session_db create  - Create session tables")
            print("  python -m scripts.setup_session_db verify  - Verify tables exist")
            print("  python -m scripts.setup_session_db drop    - Drop session tables")
    else:
        # Default: create tables
        asyncio.run(create_session_tables())
        asyncio.run(verify_tables())
