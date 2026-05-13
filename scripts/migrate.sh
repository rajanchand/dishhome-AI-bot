#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Generating initial migration if none exists..."
if [ ! -d migrations/versions ] || [ -z "$(ls -A migrations/versions/*.py 2>/dev/null || true)" ]; then
    alembic revision --autogenerate -m "initial schema"
fi

echo "Running migrations..."
alembic upgrade head

echo "Enabling TimescaleDB hypertable for device_metrics (idempotent)..."
DB_URL="${DATABASE_URL:-postgresql://dishhome:dishhome_secret@localhost:5432/dishhome_db}"
python -c "
import os, asyncio, asyncpg
async def go():
    url = os.environ.get('DATABASE_URL', '$DB_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    try:
        await conn.execute(\"\"\"
            SELECT create_hypertable('device_metrics', 'time',
                chunk_time_interval => INTERVAL '7 days',
                if_not_exists => TRUE);
        \"\"\")
        print('hypertable: ok')
    except Exception as e:
        print(f'hypertable skipped: {e}')
    finally:
        await conn.close()
asyncio.run(go())
"

echo "Seeding database..."
python scripts/seed_db.py

echo "Migration + seed complete."
