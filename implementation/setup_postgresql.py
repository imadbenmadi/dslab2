"""
PostgreSQL Setup & Verification Script

Run this FIRST before starting the system to:
1. Verify PostgreSQL is installed and running
2. Create the smart_city database
3. Create required tables and indexes
4. Test connection

Usage:
    python setup_postgresql.py
"""

import os
import sys
import time
from pathlib import Path

def check_postgresql_installed():
    """Check if PostgreSQL is installed and accessible."""
    print("Checking PostgreSQL installation...")
    try:
        import psycopg2
        print(f"[OK]  psycopg2 version {psycopg2.__version__} found")
        return True
    except ImportError:
        print("✗ psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False

def test_raw_connection(host="localhost", port=5432, user="postgres"):
    """Test raw connection to PostgreSQL server."""
    print(f"\nTesting connection to PostgreSQL at {host}:{port}...")
    
    import psycopg2
    from psycopg2 import OperationalError
    
    # Try default password first, then ask user
    for password in ["postgres", "", None]:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password or "",
                connect_timeout=5
            )
            conn.close()
            if password:
                print(f"[OK]  Connected with password: {'*' * len(password)}")
            else:
                print(f"[OK]  Connected (no password)")
            return password
        except OperationalError as e:
            err_msg = str(e)
            if "password authentication failed" in err_msg or "FATAL" in err_msg:
                continue
            else:
                print(f"✗ Connection error: {e}")
                return None
    
    print("✗ Could not connect to PostgreSQL. Is it running?")
    print("  On Windows, try:")
    print("    - Services: search 'Services' and start 'postgresql-x64-XX'")
    print("    - Or run: pg_ctl -D 'C:\\Program Files\\PostgreSQL\\XX\\data' start")
    return None

def create_database_and_tables(host="localhost", port=5432, user="postgres", password="postgres"):
    """Create smart_city database and tables."""
    import psycopg2
    from psycopg2 import sql, Error
    
    print(f"\nCreating database and tables...")
    
    try:
        # Connect to default postgres database first
        conn = psycopg2.connect(
            host=host,
            port=port,
            database="postgres",
            user=user,
            password=password,
            connect_timeout=5
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute("SELECT datname FROM pg_database WHERE datname = 'smart_city';")
        db_exists = cur.fetchone()
        
        if not db_exists:
            print("Creating database 'smart_city'...")
            cur.execute("CREATE DATABASE smart_city;")
            print("[OK]  Database created")
        else:
            print("[OK]  Database 'smart_city' already exists")
        
        cur.close()
        conn.close()
        
        # Now connect to smart_city database and create tables
        conn = psycopg2.connect(
            host=host,
            port=port,
            database="smart_city",
            user=user,
            password=password,
            connect_timeout=5
        )
        cur = conn.cursor()
        
        # Create tables
        tables = [
            """
            CREATE TABLE IF NOT EXISTS metrics_history (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                payload JSONB NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS task_events (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                payload JSONB NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS runtime_logs (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                payload JSONB NOT NULL
            );
            """,
        ]
        
        for table_sql in tables:
            cur.execute(table_sql)
            table_name = table_sql.split("CREATE TABLE IF NOT EXISTS")[1].split("(")[0].strip()
            print(f"[OK]  Table '{table_name}' created/verified")
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON metrics_history (created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON task_events (created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_logs_created_at ON runtime_logs (created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_task_events_vehicle_id ON task_events ((payload->>'vehicleId'));",
        ]
        
        for index_sql in indexes:
            cur.execute(index_sql)
        
        print("[OK]  Indexes created/verified")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("\n[OK]  Database and tables successfully initialized!")
        return True
        
    except Error as e:
        print(f"✗ Database error: {e}")
        return False

def test_redis():
    """Test Redis connection."""
    print(f"\nTesting Redis connection...")
    
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=3)
        client.ping()
        print(f"[OK]  Redis connected and responding")
        
        # Test set/get
        client.set("test_key", "test_value")
        val = client.get("test_key")
        if val == "test_value":
            print(f"[OK]  Redis read/write working")
            client.delete("test_key")
            return True
        else:
            print(f"✗ Redis value mismatch")
            return False
            
    except Exception as e:
        print(f"✗ Redis error: {e}")
        print("  Make sure Redis is running:")
        print("    - Download from https://github.com/microsoftarchive/redis/releases")
        print("    - Or use WSL: wsl ubuntu -u root redis-server")
        return False

def update_env_file(password="postgres"):
    """Update .env with correct PostgreSQL password."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("\n.env file not found, creating...")
        env_file.write_text(
            f"""# PostgreSQL Configuration
ENABLE_POSTGRES_HISTORY=true
POSTGRES_DSN=postgresql://postgres:{password}@localhost:5432/smart_city

# Redis Configuration
ENABLE_REDIS_STATE=true
REDIS_URL=redis://localhost:6379/0

# Storage Settings
STORE_BATCH_SIZE=100
STORE_FLUSH_INTERVAL_S=1.0
""")
        print(f"[OK]  .env created")
    else:
        # Update POSTGRES_DSN if not correct
        content = env_file.read_text()
        if "POSTGRES_DSN" in content:
            print("[OK]  .env already has POSTGRES_DSN")
        env_file.write_text(content)

def main():
    print("="*70)
    print("PostgreSQL Setup & Verification")
    print("="*70)
    
    # Step 1: Check psycopg2
    if not check_postgresql_installed():
        print("\n✗ Setup failed: psycopg2 not installed")
        return False
    
    # Step 2: Test connection
    password = test_raw_connection()
    if password is None:
        print("\n✗ Setup failed: Could not connect to PostgreSQL")
        return False
    
    # Step 3: Create database and tables
    if not create_database_and_tables(password=password):
        print("\n✗ Setup failed: Could not create database/tables")
        return False
    
    # Step 4: Test Redis
    redis_ok = test_redis()
    if not redis_ok:
        print("\n⚠ Redis not available (non-critical, system will work without it)")
    
    # Step 5: Update .env
    update_env_file(password)
    
    print("\n" + "="*70)
    print("[OK]  PostgreSQL setup complete!")
    print("="*70)
    print("\nYou can now run:")
    print("  python app.py proposed  # Run proposed system")
    print("  npm start               # Start React frontend")
    print("="*70 + "\n")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
