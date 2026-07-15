-- ==============================================================================
-- File: src/postgres/2-tables.sql (Updated Schema)
-- Purpose: Defines the complete database schema for v2, including all tables,
-- types, and performance-enhancing indexes.
-- Corrected the syntax for the partial unique constraint on user_application.
-- ==============================================================================

-- Drop tables if they exist (in reverse order of creation due to dependencies)
DROP TABLE IF EXISTS file_status CASCADE;
DROP TYPE IF EXISTS file_status_type CASCADE;
DROP TYPE IF EXISTS application_status CASCADE;
DROP TYPE IF EXISTS account_type CASCADE;
DROP TABLE IF EXISTS user_application CASCADE;
DROP TABLE IF EXISTS file CASCADE;
DROP TABLE IF EXISTS cost_metric CASCADE;
DROP TABLE IF EXISTS collection CASCADE;
DROP TABLE IF EXISTS egress CASCADE;
DROP TABLE IF EXISTS cueuser_provider CASCADE;
DROP TABLE IF EXISTS provider CASCADE;
DROP TABLE IF EXISTS cueuser_ngroup CASCADE;
DROP TABLE IF EXISTS cueuser_role CASCADE;
DROP TABLE IF EXISTS role_privilege CASCADE;
DROP TABLE IF EXISTS privilege CASCADE;
DROP TABLE IF EXISTS api_key CASCADE;
DROP TABLE IF EXISTS api_key_type CASCADE;
DROP TABLE IF EXISTS role CASCADE;
DROP TABLE IF EXISTS ngroup CASCADE;
DROP TABLE IF EXISTS cueuser_auth CASCADE; 
DROP TABLE IF EXISTS cueuser CASCADE;


-- ==============================================================================
-- Table Definitions
-- ==============================================================================

CREATE TABLE IF NOT EXISTS cueuser (
    id UUID NOT NULL,
    email VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    registered TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cueusername VARCHAR NOT NULL,
    edpub_id VARCHAR,
    PRIMARY KEY (id),
    UNIQUE (email),
    UNIQUE (cueusername),
    UNIQUE (edpub_id)
);

-- Delete later.
CREATE TABLE IF NOT EXISTS cueuser_auth (
    id UUID NOT NULL,
    refresh_token VARCHAR,
    last_login TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Use TIMESTAMPTZ
    PRIMARY KEY (id),
    FOREIGN KEY (id) REFERENCES cueuser(id)
);



CREATE TABLE IF NOT EXISTS ngroup (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    short_name VARCHAR NOT NULL,
    long_name VARCHAR NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (short_name),
    UNIQUE (long_name)
);

CREATE TABLE IF NOT EXISTS cueuser_ngroup (
    cueuser_id UUID NOT NULL,
    ngroup_id UUID NOT NULL,
    PRIMARY KEY (cueuser_id, ngroup_id),
    FOREIGN KEY (cueuser_id) REFERENCES cueuser(id) ON DELETE CASCADE,
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS role (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    short_name VARCHAR NOT NULL,
    long_name VARCHAR NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (short_name),
    UNIQUE (long_name)
);

CREATE TYPE api_key_type AS ENUM ('personal', 'managed_user', 'proxy');

CREATE TABLE IF NOT EXISTS api_key (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    key_hash VARCHAR NOT NULL,
    prefix VARCHAR(10) NOT NULL,
    name VARCHAR(255) NOT NULL,
    scopes VARCHAR[] NOT NULL,
    key_display_suffix VARCHAR(4) NULL,
    key_type api_key_type NOT NULL,

    -- "Created For"
    user_id UUID NULL, 
    proxy_user_name VARCHAR(255) NULL,

    -- "Created By"
    created_by_user_id UUID NOT NULL,

    -- Group association
    ngroup_id UUID NULL,

    -- Timestamps & Status
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    revoked_at TIMESTAMPTZ NULL,

    PRIMARY KEY (id),
    UNIQUE (key_hash),
    FOREIGN KEY (user_id) REFERENCES cueuser(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES cueuser(id) ON DELETE CASCADE,
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id) ON DELETE SET NULL,

    -- The rule for 'personal' keys now correctly allows an ngroup_id.
    CONSTRAINT chk_key_owner CHECK (
        (key_type = 'personal' AND user_id IS NOT NULL AND proxy_user_name IS NULL AND ngroup_id IS NOT NULL) OR
        (key_type = 'managed_user' AND user_id IS NOT NULL AND proxy_user_name IS NULL AND ngroup_id IS NOT NULL) OR
        (key_type = 'proxy' AND user_id IS NULL AND proxy_user_name IS NOT NULL AND ngroup_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS cueuser_role (
    cueuser_id UUID NOT NULL,
    role_id UUID NOT NULL,
    PRIMARY KEY (cueuser_id, role_id),
    FOREIGN KEY (cueuser_id) REFERENCES cueuser(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS privilege (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    privilege VARCHAR NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (privilege)
);

CREATE TABLE IF NOT EXISTS role_privilege(   
    privilege_id UUID NOT NULL,
    role_id UUID NOT NULL,
    PRIMARY KEY (privilege_id, role_id),
    FOREIGN KEY (privilege_id) REFERENCES privilege(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS provider (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    ngroup_id UUID NOT NULL,
    short_name VARCHAR NOT NULL,
    long_name VARCHAR NOT NULL,
    can_upload BOOLEAN NOT NULL DEFAULT FALSE,
    point_of_contact UUID NOT NULL,
    reason VARCHAR,
    last_block_notification_at TIMESTAMPTZ,
    PRIMARY KEY (id),
    FOREIGN KEY (point_of_contact) REFERENCES cueuser(id),
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id),
    UNIQUE (short_name),
    UNIQUE (long_name)
);

CREATE TABLE IF NOT EXISTS cueuser_provider (
    cueuser_id UUID NOT NULL,
    provider_id UUID NOT NULL,
    PRIMARY KEY (cueuser_id, provider_id),
    FOREIGN KEY (cueuser_id) REFERENCES cueuser(id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES provider(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS egress (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    type VARCHAR NOT NULL,
    path VARCHAR NOT NULL,
    config JSONB NOT NULL,
    ngroup_id UUID NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id)
);

CREATE TABLE IF NOT EXISTS collection (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    ngroup_id UUID NOT NULL,
    egress_id UUID NOT NULL,
    short_name VARCHAR NOT NULL,
    provider_id UUID NOT NULL,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id),
    FOREIGN KEY (egress_id) REFERENCES egress(id),
    FOREIGN KEY (provider_id) REFERENCES provider(id)
);

CREATE TABLE IF NOT EXISTS file (
    id UUID NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    cueuser_uploaded UUID NOT NULL,
    size_bytes BIGINT NOT NULL,
    collection_id UUID NOT NULL,
    collection_path VARCHAR,
    edpub BOOLEAN NOT NULL DEFAULT FALSE,
    checksum VARCHAR NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (cueuser_uploaded) REFERENCES cueuser(id),
    FOREIGN KEY (collection_id) REFERENCES collection(id)
);

CREATE TYPE application_status AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE account_type AS ENUM ('daac', 'provider');

CREATE TABLE IF NOT EXISTS user_application (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID,
    email VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    applied TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR NOT NULL,
    status application_status NOT NULL DEFAULT 'pending',
    ngroup_id UUID NOT NULL,
    provider_id UUID NULL,
    justification TEXT NOT NULL,
    account_type account_type,
    edpub_id VARCHAR,
    PRIMARY KEY (id),
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id),
    FOREIGN KEY (provider_id) REFERENCES provider(id)
);

CREATE TYPE file_status_type AS ENUM (
    'uploading',
    'unscanned',
    'clean',
    'infected',
    'scan_failed',
    'distributed'
);

CREATE TABLE IF NOT EXISTS file_status (
    id UUID NOT NULL,
    upload_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scan_start TIMESTAMPTZ,
    scan_end TIMESTAMPTZ,
    egress_start TIMESTAMPTZ,
    status file_status_type NOT NULL,
    scan_results JSONB,
    notification_sent_at TIMESTAMPTZ,

    PRIMARY KEY (id),
    FOREIGN KEY (id) REFERENCES file(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cost_metric (
    file_id UUID NOT NULL,
    scanner_cost NUMERIC(10, 6),
    aws_transfer_cost NUMERIC(10, 6),
    metric_recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id),
    FOREIGN KEY (file_id) REFERENCES file(id) ON DELETE CASCADE
);

-- ==============================================================================
-- Performance Indexes
-- ==============================================================================

-- Indexes for the cueuser table
CREATE INDEX IF NOT EXISTS idx_cueuser_email ON cueuser(email);
CREATE INDEX IF NOT EXISTS idx_cueuser_cueusername ON cueuser(cueusername);

-- Index for quickly finding a user's keys
CREATE INDEX IF NOT EXISTS idx_api_key_user_id ON api_key(user_id);

-- --- CHANGE: Replaced partial constraint with a partial UNIQUE INDEX ---
-- This enforces that a user can only have one application in the 'pending' state at a time.
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_pending_application ON user_application(user_id) WHERE (status = 'pending');

-- Index for admins listing applications by group and status
CREATE INDEX IF NOT EXISTS idx_user_application_ngroup_status ON user_application(ngroup_id, status);

-- Indexes for common foreign key lookups to speed up JOINs
CREATE INDEX IF NOT EXISTS idx_file_collection_id ON file(collection_id);
CREATE INDEX IF NOT EXISTS idx_collection_provider_id ON collection(provider_id);
CREATE INDEX IF NOT EXISTS idx_provider_ngroup_id ON provider(ngroup_id);

-- New index to speed up finding files that need notification
CREATE INDEX IF NOT EXISTS idx_file_status_pending_notification
ON file_status(status)
WHERE (status = 'infected' AND notification_sent_at IS NULL);

-- Indexes to speed up metrics sorting and filtering
CREATE INDEX IF NOT EXISTS idx_collection_ngroup_id ON collection(ngroup_id);
CREATE INDEX IF NOT EXISTS idx_file_status_upload_time ON file_status(upload_time);

-- Partial unique index to enforce unique short_name for active (non-deleted) collections
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_collection_short_name 
ON collection(short_name) 
WHERE (is_deleted = FALSE);