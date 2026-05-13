-- PostgreSQL initialization script (executed on first container start)
-- Enables required extensions before Alembic migrations run

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
