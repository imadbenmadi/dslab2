# PostgreSQL Setup

Configure PostgreSQL database for metrics storage.

## Quick Setup (2 min)

```bash
python setup_postgresql.py
```

This automatically:

- Checks PostgreSQL is installed
- Tests connection
- Creates `smart_city` database
- Creates tables and indexes
- Tests Redis
- Updates .env

## Manual Setup

### Windows

1. **Start PostgreSQL Service**
    - Press `Win` → type "Services"
    - Find "postgresql-x64-XX"
    - Right-click → Start

2. **Create Database**

    ```bash
    psql -U postgres
    postgres=# CREATE DATABASE smart_city;
    postgres=# \connect smart_city
    ```

3. **Create Tables**

    ```sql
    CREATE TABLE metrics_history (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        payload JSONB NOT NULL
    );

    CREATE TABLE task_events (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        payload JSONB NOT NULL
    );

    CREATE TABLE runtime_logs (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        payload JSONB NOT NULL
    );

    -- Create indexes for fast queries
    CREATE INDEX idx_metrics_created_at ON metrics_history (created_at DESC);
    CREATE INDEX idx_tasks_created_at ON task_events (created_at DESC);
    CREATE INDEX idx_logs_created_at ON runtime_logs (created_at DESC);
    SELECT 'Tables created successfully';
    ```

### Linux / Mac

```bash
# Ubuntu
sudo service postgresql start

# Mac (Homebrew)
brew services start postgresql

# Then create database
createdb -U postgres smart_city
psql -U postgres -d smart_city << EOF
CREATE TABLE metrics_history (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    payload JSONB NOT NULL
);
... (SQL above)
EOF
```

## Configuration

Edit `.env`:

```ini
# PostgreSQL
ENABLE_POSTGRES_HISTORY=true
POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/smart_city

# Optional: Redis
ENABLE_REDIS_STATE=true
REDIS_URL=redis://localhost:6379/0

# Storage tuning
STORE_BATCH_SIZE=100
STORE_FLUSH_INTERVAL_S=1.0
```

## Verification

```bash
# Check connection
psql -U postgres -d smart_city -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';"
# Expected: Should show 3 tables

# Check data (has entries after running system)
psql -U postgres -d smart_city -c "SELECT COUNT(*) FROM metrics_history;"
```

## Troubleshooting

### Connection Refused

```bash
# Check if PostgreSQL is running
psql --version  # Should work if installed

# Start service:
# Windows: Services → postgresql → Start
# Linux: sudo systemctl start postgresql
# Mac: brew services start postgresql
```

### Authentication Error

```bash
# If password wrong, check .env
POSTGRES_DSN=postgresql://postgres:YOUR_PASSWORD@localhost:5432/smart_city

# Or reset PostgreSQL password
sudo -u postgres psql
postgres=# ALTER USER postgres WITH PASSWORD 'postgres';
```

### Database Doesn't Exist

```bash
createdb -U postgres smart_city
```

### Tables Missing

```bash
psql -U postgres -d smart_city < setup_tables.sql
```

## Backup & Restore

```bash
# Backup database
pg_dump -U postgres smart_city > smart_city_backup.sql

# Restore
psql -U postgres smart_city < smart_city_backup.sql

# Backup specific table
pg_dump -U postgres -t metrics_history smart_city > metrics_backup.sql
```

## Query Examples

```bash
# Total metrics collected
psql -U postgres -d smart_city -c "SELECT COUNT(*) FROM metrics_history;"

# Last 10 measurements
psql -U postgres -d smart_city -c "SELECT * FROM metrics_history ORDER BY created_at DESC LIMIT 10;"

# Metrics per system
psql -U postgres -d smart_city -c "
  SELECT
    payload->>'systemType' as system,
    COUNT(*) as count,
    AVG((payload->>'avgLatency')::float) as avg_latency
  FROM metrics_history
  GROUP BY payload->>'systemType';"
```

---

See [SETUP.md](./SETUP.md) for full installation guide.
