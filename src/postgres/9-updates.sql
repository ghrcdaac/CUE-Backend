ALTER TABLE file_status
    ADD COLUMN scan_results JSONB;

ALTER TABLE collection
    ADD COLUMN active BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE provider
    ADD COLUMN ngroup_id UUID NOT NULL;
    ADD FOREIGN KEY (ngroup_id) REFERENCES ngroup(id);

CREATE TABLE IF NOT EXISTS user_application (
    id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
    email VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    applied TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR NOT NULL,
    acc_type acc_type NOT NULL,
    ngroup_id UUID NOT NULL,
    justification TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id),
)