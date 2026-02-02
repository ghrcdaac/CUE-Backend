#!/usr/bin/env bash
set -euo pipefail

# Require TEST_* env vars
: "${POSTGRES_DB_TEST:?POSTGRES_DB_TEST is required}"
: "${POSTGRES_USER_TEST:?POSTGRES_USER_TEST is required}"
: "${POSTGRES_PASSWORD_TEST:?TPOSTGRES_PASSWORD_TEST is required}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v db="$POSTGRES_DB_TEST" -v user="$POSTGRES_USER_TEST" -v pass="$POSTGRES_PASSWORD_TEST" <<'PSQL'
\set ON_ERROR_STOP on

-- Create role if missing
SELECT 'CREATE ROLE ' || quote_ident(:'user') || ' LOGIN PASSWORD ' || quote_literal(:'pass')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'user');
\gexec

-- Ensure password (safe even if role existed)
ALTER ROLE :"user" WITH LOGIN PASSWORD :'pass';

-- Create database if missing, owned by the role
SELECT 'CREATE DATABASE ' || quote_ident(:'db') || ' OWNER ' || quote_ident(:'user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db');
\gexec
PSQL

SCHEMA_DIR="/docker-entrypoint-initdb.d/"
echo "Applying SQL to $POSTGRES_DB_TEST"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER_TEST" --dbname "$POSTGRES_DB_TEST" -f "${SCHEMA_DIR}1-init.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER_TEST" --dbname "$POSTGRES_DB_TEST" -f "${SCHEMA_DIR}2-tables.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER_TEST" --dbname "$POSTGRES_DB_TEST" -f "${SCHEMA_DIR}4-functions.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER_TEST" --dbname "$POSTGRES_DB_TEST" -f "${SCHEMA_DIR}5-triggers.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER_TEST" --dbname "$POSTGRES_DB_TEST" -f "${SCHEMA_DIR}6-aggregates.sql"
# psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER_TEST" --dbname "$POSTGRES_DB_TEST" -f "${SCHEMA_DIR}7-seed.sql"
# psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER_TEST" --dbname "$POSTGRES_DB_TEST" -f "8-localseed.sql"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER_TEST" --dbname "$POSTGRES_DB_TEST" -f "9-updates.sql"

# Loop over sql files
# for file in $(find "$SCHEMA_DIR" -maxdepth 1 -type f -name '*.sql' | sort); do
#   echo "  - $file"
#   psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER_TEST" --dbname "$POSTGRES_DB_TEST" -f "$file"
# done  