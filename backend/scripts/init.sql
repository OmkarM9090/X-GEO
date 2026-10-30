<!--
  Executed by the official postgres image on first container start (before
  Alembic runs). The initial migration enables the same extensions, so this file
  is a belt-and-braces guarantee that they exist for a brand new cluster.
-->
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Separate database used by the integration/E2E test suite (see tests/conftest.py).
-- CREATE DATABASE has no IF NOT EXISTS, but this script only runs once, on an
-- empty data directory, so it cannot collide.
CREATE DATABASE xgeo_test_db OWNER CURRENT_USER;

\connect xgeo_test_db
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
