ALTER TABLE file_status
    ADD COLUMN scan_results JSONB;

ALTER TABLE collection
    ADD COLUMN active BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE provider
    ADD COLUMN ngroup_id UUID NOT NULL;
    ADD FOREIGN KEY (ngroup_id) REFERENCES ngroup(id);

-- Update the 'registered' column in the 'cueuser' table to TIMESTAMPTZ
ALTER TABLE cueuser
ALTER COLUMN registered TYPE TIMESTAMPTZ,
