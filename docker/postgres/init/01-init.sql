-- Initial database setup for AI Enterprise Studio
-- This script runs when PostgreSQL container first starts

-- Create additional databases if needed
-- CREATE DATABASE ai_studio_test;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ai_studio_db TO ai_studio;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'AI Enterprise Studio database initialized successfully';
END $$;
