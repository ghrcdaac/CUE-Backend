ALTER TABLE file_status
    ADD COLUMN IF NOT EXISTS scan_results JSONB;

ALTER TABLE collection
    ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT FALSE;

-- Update the 'registered' column in the 'cueuser' table to TIMESTAMPTZ
ALTER TABLE cueuser
ALTER COLUMN registered TYPE TIMESTAMPTZ;

ALTER TABLE provider
    ADD COLUMN IF NOT EXISTS ngroup_id UUID NOT NULL;

--  `IF NOT EXISTS` is throwing error for the following statements. using PL/pgSQL to safely execute the logic
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'provider_ngroup_id_fkey'
          AND table_name = 'provider'
    ) THEN
        ALTER TABLE provider
        ADD CONSTRAINT provider_ngroup_id_fkey FOREIGN KEY (ngroup_id) REFERENCES ngroup(id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'application_status') THEN
        CREATE TYPE application_status AS ENUM ('pending', 'approved', 'rejected');
    END IF;
     IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'account_type') THEN
        CREATE TYPE account_type AS ENUM ('daac', 'provider');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_application') THEN
        CREATE TABLE user_application (
            id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
            email VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            applied TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            username VARCHAR NOT NULL,
            status application_status NOT NULL DEFAULT 'pending',
            ngroup_id UUID NOT NULL,
            provider_id UUID NULL,  -- Allow NULL initially
            justification TEXT NOT NULL,
            account_type account_type, -- added account type
            is_spam BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (id),
            FOREIGN KEY (ngroup_id) REFERENCES ngroup(id),
            FOREIGN KEY (provider_id) REFERENCES provider(id) -- Add FK constraint
        );
    END IF;
END $$;

ALTER TABLE user_application
ALTER COLUMN applied TYPE TIMESTAMPTZ;

ALTER TABLE user_application
ADD COLUMN IF NOT EXISTS edpub_id VARCHAR;

ALTER TABLE user_application
ADD COLUMN IF NOT EXISTS is_spam BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_user_application_email_spam
ON user_application(LOWER(email))
WHERE (is_spam = TRUE);

ALTER TABLE cueuser_auth
ALTER COLUMN last_login TYPE TIMESTAMPTZ;

-- Create type for file status if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'file_status_type') THEN
        CREATE TYPE file_status_type AS ENUM (
            'unscanned',       -- File has been uploaded but not yet scanned
            'clean',           -- File has been scanned and no issues were found
            'infected',        -- File has been scanned and found to be infected
            'scan_failed',     -- File could not be scanned (e.g., due to an error)
            'distributed'    -- File has been distributed
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'file_status' AND column_name = 'upload_time') THEN
        ALTER TABLE file_status ADD COLUMN upload_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

ALTER TABLE file_status
ALTER COLUMN scan_start TYPE TIMESTAMPTZ,
ALTER COLUMN scan_end TYPE TIMESTAMPTZ,
ALTER COLUMN egress_start TYPE TIMESTAMPTZ,
ALTER COLUMN status TYPE file_status_type USING status::text::file_status_type;


BEGIN;

UPDATE cueuser_auth SET refresh_token = NULL WHERE refresh_token = '';

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_name = 'cueuser_auth'
      AND constraint_name = 'cueuser_auth_pkey'  -- Check for the PRIMARY KEY
      AND constraint_type = 'PRIMARY KEY'
  ) THEN
    -- Check if refresh_token is part of a composite primary key (it shouldn't be,
    -- but this adds extra safety).  If it's NOT part of the primary key, proceed.
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.key_column_usage
        WHERE table_name = 'cueuser_auth'
          AND constraint_name = 'cueuser_auth_pkey'
          AND column_name = 'refresh_token'
    ) THEN
        -- Now we can safely drop the NOT NULL constraint
        ALTER TABLE cueuser_auth
        ALTER COLUMN refresh_token DROP NOT NULL;
    END IF;
  END IF;
END $$;

COMMIT;

-- ALTER TABLE user_application ADD COLUMN user_id UUID;

-- ALTER TYPE file_status_type ADD VALUE 'uploading' BEFORE 'unscanned';


-- ALTER TABLE file_status
-- ADD COLUMN notification_sent_at TIMESTAMPTZ;

-- ALTER TABLE provider
-- ADD COLUMN last_block_notification_at TIMESTAMPTZ;

-- CREATE INDEX IF NOT EXISTS idx_file_status_pending_notification
-- ON file_status(status)
-- WHERE (status = 'infected' AND notification_sent_at IS NULL);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_name_trgm ON file USING gin (name gin_trgm_ops);
-- Indexes to speed up metrics sorting and filtering
CREATE INDEX IF NOT EXISTS idx_collection_ngroup_id ON collection(ngroup_id);
CREATE INDEX IF NOT EXISTS idx_file_status_upload_time ON file_status(upload_time);

-- Soft delete support for collection
ALTER TABLE collection ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

-- Replace standard unique constraint with partial unique index to allow reuse of deleted short_names
ALTER TABLE collection DROP CONSTRAINT IF EXISTS collection_short_name_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_collection_short_name 
ON collection(short_name) 
WHERE (is_deleted = FALSE);


-- ===== GUI support: provider mappings — added 2026-10-29 =====
-- Run each [GUI-n] statement on its own, in order (SIT -> UAT -> PROD). Every statement is idempotent.
-- Existing tables (file, file_status, collection, cueuser_provider, ...) keep their data and constraints.

-- [GUI-1] collection <-> provider many-to-many (collection.provider_id stays as the "primary" provider)
CREATE TABLE IF NOT EXISTS collection_provider (
    collection_id UUID NOT NULL REFERENCES collection(id) ON DELETE CASCADE,
    provider_id   UUID NOT NULL REFERENCES provider(id)   ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by    UUID NULL REFERENCES cueuser(id) ON DELETE SET NULL,
    PRIMARY KEY (collection_id, provider_id)
);

-- [GUI-2]
CREATE INDEX IF NOT EXISTS idx_collection_provider_provider_id ON collection_provider(provider_id);

-- [GUI-3]
CREATE INDEX IF NOT EXISTS idx_cueuser_provider_provider_id ON cueuser_provider(provider_id);

-- [GUI-4] audit history for BOTH mapping tables (rows are never deleted from here)
CREATE TABLE IF NOT EXISTS mapping_history (
    id           UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    mapping_type VARCHAR NOT NULL CHECK (mapping_type IN ('collection_provider','cueuser_provider')),
    left_id      UUID NOT NULL,   -- collection_id or cueuser_id
    right_id     UUID NOT NULL,   -- provider_id
    action       VARCHAR NOT NULL CHECK (action IN ('added','removed','primary_set','primary_unset','backfilled')),
    actor_id     UUID NULL,       -- cueuser who made the change (NULL = system/backfill)
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details      JSONB NULL
);

-- [GUI-5]
CREATE INDEX IF NOT EXISTS idx_mapping_history_lookup ON mapping_history(mapping_type, left_id, right_id, occurred_at DESC);

-- [GUI-orphans] read-only: collections whose provider_id points to a provider that no longer exists.
-- These are skipped by GUI-6 and GUI-7 (they can't upload today either). Fix them separately if needed.
SELECT c.id, c.short_name, c.provider_id, c.active, c.is_deleted
FROM collection c
LEFT JOIN provider p ON p.id = c.provider_id
WHERE c.provider_id IS NOT NULL AND p.id IS NULL;

-- [GUI-6] backfill (re-runnable); only collections whose provider exists
INSERT INTO collection_provider (collection_id, provider_id)
SELECT c.id, c.provider_id
FROM collection c
JOIN provider p ON p.id = c.provider_id
ON CONFLICT DO NOTHING;

-- [GUI-7] one read path for "which providers serve which collection"
CREATE OR REPLACE VIEW v_collection_provider AS
    SELECT collection_id, provider_id FROM collection_provider
    UNION
    SELECT c.id AS collection_id, c.provider_id
    FROM collection c
    JOIN provider p ON p.id = c.provider_id;

-- [GUI-check] read-only: expected = actual after GUI-6 (orphans from GUI-orphans are not counted)
SELECT (SELECT count(*) FROM collection c JOIN provider p ON p.id = c.provider_id) AS expected,
       (SELECT count(*) FROM collection c JOIN collection_provider cp ON cp.collection_id = c.id AND cp.provider_id = c.provider_id) AS actual;