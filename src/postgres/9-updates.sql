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
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_application') THEN
        CREATE TABLE user_application (
            id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
            email VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            applied TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            username VARCHAR NOT NULL,
            status application_status NOT NULL DEFAULT 'pending',
            ngroup_id UUID NOT NULL,
            justification TEXT NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY (ngroup_id) REFERENCES ngroup(id)
        );
    END IF;
END $$;

ALTER TABLE user_application
ALTER COLUMN applied TYPE TIMESTAMPTZ;

ALTER TABLE cueuser_auth
ALTER COLUMN LAST_LOGIN TYPE TIMESTAMPTZ;

ALTER TABLE file_status
ALTER COLUMN upload_time TYPE TIMESTAMPTZ,
ALTER COLUMN scan_start TYPE TIMESTAMPTZ,
ALTER COLUMN scan_end TYPE TIMESTAMPTZ,
ALTER COLUMN egress_start TYPE TIMESTAMPTZ;
