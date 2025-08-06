-- Drop tables if they exist (in reverse order of creation due to dependencies)
DROP TABLE IF EXISTS file_status CASCADE;
DROP TYPE IF EXISTS file_status_type CASCADE;
DROP TYPE IF EXISTS application_status CASCADE;
DROP TYPE IF EXISTS account_type CASCADE;
DROP TABLE IF EXISTS user_application CASCADE;
DROP TABLE IF EXISTS file CASCADE;
DROP TABLE IF EXISTS collection CASCADE;
DROP TABLE IF EXISTS egress CASCADE;
DROP TABLE IF EXISTS cueuser_provider CASCADE;
DROP TABLE IF EXISTS provider CASCADE;
DROP TABLE IF EXISTS cueuser_ngroup CASCADE;
DROP TABLE IF EXISTS cueuser_role CASCADE;
DROP TABLE IF EXISTS role_privilege CASCADE;
DROP TABLE IF EXISTS privilege CASCADE;
DROP TABLE IF EXISTS role CASCADE;
DROP TABLE IF EXISTS ngroup CASCADE;
DROP TABLE IF EXISTS cueuser_auth CASCADE;
DROP TABLE IF EXISTS cueuser CASCADE;
DROP TABLE IF EXISTS notification CASCADE;


CREATE TABLE IF NOT EXISTS cueuser (
    id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
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

CREATE TABLE IF NOT EXISTS cueuser_auth (
    id UUID NOT NULL,
    refresh_token VARCHAR,
    last_login TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Use TIMESTAMPTZ
    PRIMARY KEY (id),
    FOREIGN KEY (id) REFERENCES cueuser(id)
);

CREATE TABLE IF NOT EXISTS ngroup (
    id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
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
    FOREIGN KEY (cueuser_id) REFERENCES cueuser(id),
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id)
);

CREATE TABLE IF NOT EXISTS role (
    id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
    short_name VARCHAR NOT NULL,
    long_name VARCHAR NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (short_name),
    UNIQUE (long_name)
);

CREATE TABLE IF NOT EXISTS cueuser_role (
    cueuser_id UUID NOT NULL,
    role_id UUID NOT NULL,
    PRIMARY KEY (cueuser_id, role_id),
    FOREIGN KEY (cueuser_id) REFERENCES cueuser(id),
    FOREIGN KEY (role_id) REFERENCES role(id)
);

CREATE TABLE IF NOT EXISTS privilege (
    privilege VARCHAR NOT NULL,
    PRIMARY KEY (privilege),
    UNIQUE (privilege)
);

CREATE TABLE IF NOT EXISTS role_privilege(
    privilege VARCHAR NOT NULL,
    role_id UUID NOT NULL,
    PRIMARY KEY (privilege, role_id),
    FOREIGN KEY (privilege) REFERENCES privilege(privilege),
    FOREIGN KEY (role_id) REFERENCES role(id)
);

CREATE TABLE IF NOT EXISTS provider (
    id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
    ngroup_id UUID NOT NULL,
    short_name VARCHAR NOT NULL,
    long_name VARCHAR NOT NULL,
    can_upload BOOLEAN NOT NULL DEFAULT FALSE,
    point_of_contact UUID NOT NULL,
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
    FOREIGN KEY (cueuser_id) REFERENCES cueuser(id),
    FOREIGN KEY (provider_id) REFERENCES provider(id)
);

CREATE TABLE IF NOT EXISTS egress (
    id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
    type VARCHAR NOT NULL,
    path VARCHAR NOT NULL,
    config JSONB NOT NULL,
    ngroup_id UUID NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id)
);

CREATE TABLE IF NOT EXISTS collection (
    id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
    ngroup_id UUID NOT NULL,
    egress_id UUID NOT NULL,
    short_name VARCHAR NOT NULL,
    provider_id UUID NOT NULL,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id),
    FOREIGN KEY (egress_id) REFERENCES egress(id),
    FOREIGN KEY (provider_id) REFERENCES provider(id),
    UNIQUE (short_name)
);

CREATE TABLE IF NOT EXISTS file (
    id UUID NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    cueuser_uploaded UUID NOT NULL,
    size_bytes INT NOT NULL,
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
    id UUID NOT NULL DEFAULT UUID_GENERATE_V4(),
    email VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    applied TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR NOT NULL,
    status application_status NOT NULL DEFAULT 'pending',
    ngroup_id UUID NOT NULL,
    provider_id UUID NULL,  -- Allow NULL
    justification TEXT NOT NULL,
    account_type account_type, -- use the enum
    edpub_id VARCHAR,
    PRIMARY KEY (id),
    FOREIGN KEY (ngroup_id) REFERENCES ngroup(id),
    FOREIGN KEY (provider_id) REFERENCES provider(id)
);



-- Create type for file status
CREATE TYPE file_status_type AS ENUM (
    'unscanned',       -- File has been uploaded but not yet scanned
    'clean',           -- File has been scanned and no issues were found
    'infected',        -- File has been scanned and found to be infected
    'scan_failed',     -- File could not be scanned (e.g., due to an error)
    'distributed'    -- File has been distributed
);

CREATE TABLE IF NOT EXISTS file_status (
    id UUID NOT NULL,
    upload_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Use TIMESTAMPTZ
    scan_start TIMESTAMPTZ,  -- Use TIMESTAMPTZ
    scan_end TIMESTAMPTZ,    -- Use TIMESTAMPTZ
    egress_start TIMESTAMPTZ, -- Use TIMESTAMPTZ
    status file_status_type NOT NULL,
    scan_results JSONB,
    PRIMARY KEY (id),
    FOREIGN KEY (id) REFERENCES file(id)
);

CREATE TYPE report_frequency AS ENUM (
    'daily',       
    'weekly',           
    'bi_weekly',        
    'monthly',    
    'none'    
);

Create TYPE report_type as ENUM (
    'infected_file'
);

CREATE TABLE IF NOT EXISTS notification (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cueuser_id UUID NOT NULL,
    report_type report_type NOT NULL,  -- infected, clean, failed, etc.
    frequency report_frequency NOT NULL,   -- daily, weekly, biweekly, monthly, none 
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    FOREIGN KEY (cueuser_id) REFERENCES cueuser(id),
    UNIQUE (cueuser_id, report_type)
);

CREATE UNIQUE INDEX user_id ON notification (cueuser_id, id);