-- Privilege

INSERT INTO privilege (id, privilege) VALUES
    ('a1a1a1a1-0000-0000-0000-000000000001', 'user:create'),
    ('a1a1a1a1-0000-0000-0000-000000000002', 'user:read'),
    ('a1a1a1a1-0000-0000-0000-000000000003', 'user:update'),
    ('a1a1a1a1-0000-0000-0000-000000000004', 'user:delete'),
    ('a1a1a1a1-0000-0000-0000-000000000005', 'user:assign_role'),
    ('a1a1a1a1-0000-0000-0000-000000000006', 'user:assign_ngroup'),
    ('a1a1a1a1-0000-0000-0000-000000000007', 'user:suspend'),
    ('a1a1a1a1-0000-0000-0000-000000000008', 'user:reinstate'),
    ('a1a1a1a1-0000-0000-0000-000000000009', 'application:read'),
    ('a1a1a1a1-0000-0000-0000-000000000010', 'application:approve'),
    ('a1a1a1a1-0000-0000-0000-000000000011', 'provider:create'),
    ('a1a1a1a1-0000-0000-0000-000000000012', 'provider:read'),
    ('a1a1a1a1-0000-0000-0000-000000000013', 'provider:update'),
    ('a1a1a1a1-0000-0000-0000-000000000014', 'provider:delete'),
    ('a1a1a1a1-0000-0000-0000-000000000015', 'collection:create'),
    ('a1a1a1a1-0000-0000-0000-000000000016', 'collection:read'),
    ('a1a1a1a1-0000-0000-0000-000000000017', 'collection:update'),
    ('a1a1a1a1-0000-0000-0000-000000000018', 'collection:delete'),
    ('a1a1a1a1-0000-0000-0000-000000000019', 'egress:create'),
    ('a1a1a1a1-0000-0000-0000-000000000020', 'egress:read'),
    ('a1a1a1a1-0000-0000-0000-000000000021', 'egress:update'),
    ('a1a1a1a1-0000-0000-0000-000000000022', 'egress:delete'),
    ('a1a1a1a1-0000-0000-0000-000000000023', 'file:upload'),
    ('a1a1a1a1-0000-0000-0000-000000000024', 'file:read'),
    ('a1a1a1a1-0000-0000-0000-000000000025', 'file:read_all'),
    ('a1a1a1a1-0000-0000-0000-000000000026', 'scan:read'),
    ('a1a1a1a1-0000-0000-0000-000000000027', 'scan:read_all'),
    ('a1a1a1a1-0000-0000-0000-000000000028', 'metrics:read'),
    ('a1a1a1a1-0000-0000-0000-000000000029', 'role:create'),
    ('a1a1a1a1-0000-0000-0000-000000000030', 'role:read'),
    ('a1a1a1a1-0000-0000-0000-000000000031', 'role:update'),
    ('a1a1a1a1-0000-0000-0000-000000000032', 'role:delete'),
    ('a1a1a1a1-0000-0000-0000-000000000033', 'ngroup:create'),
    ('a1a1a1a1-0000-0000-0000-000000000034', 'ngroup:read'),
    ('a1a1a1a1-0000-0000-0000-000000000035', 'ngroup:update'),
    ('a1a1a1a1-0000-0000-0000-000000000036', 'ngroup:delete'),
    ('a1a1a1a1-0000-0000-0000-000000000037', 'file:delete'),
    ('a1a1a1a1-0000-0000-0000-000000000040', 'archive:query');

-- Roles
INSERT INTO role (id, short_name, long_name) VALUES
    ('c924d0d3-55af-49f3-bec1-d7fd4ed475e2', 'admin', 'Admin'),
    ('39677929-ba9b-426d-8c18-f607d669fcce', 'security', 'Security'),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'daac_manager', 'DAAC Manager'),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'daac_staff', 'DAAC Staff'),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', 'daac_observer', 'DAAC Observer'),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', 'provider', 'Provider');

-- Role to Privilege Mappings
-- Admin (has all privileges)
INSERT INTO role_privilege (role_id, privilege_id) SELECT 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2', id FROM privilege;

-- Security
INSERT INTO role_privilege (role_id, privilege_id) VALUES
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:suspend')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:reinstate')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'file:read_all')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'scan:read_all')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'metrics:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'file:delete'));

-- DAAC Manager
INSERT INTO role_privilege (role_id, privilege_id) VALUES
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'application:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'application:approve')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:create')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:update')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:assign_role')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'provider:create')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'provider:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'provider:update')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'collection:create')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'collection:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'collection:update')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'collection:delete')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'egress:create')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'egress:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'egress:update')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'egress:delete')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'file:upload')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'file:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'scan:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'metrics:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'file:delete')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'archive:query')); 

-- DAAC Staff
INSERT INTO role_privilege (role_id, privilege_id) VALUES
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:create')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:read')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:update')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'collection:create')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'collection:read')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'collection:update')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'collection:delete')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'egress:create')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'egress:read')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'egress:update')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'egress:delete')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'file:upload')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'file:read')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'scan:read')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'metrics:read')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'file:delete')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'archive:query')); 

-- DAAC Observer
INSERT INTO role_privilege (role_id, privilege_id) VALUES
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'provider:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'collection:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'egress:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'file:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'scan:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'metrics:read'));

-- Provider
INSERT INTO role_privilege (role_id, privilege_id) VALUES
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'provider:read')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'file:upload')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'file:read')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'scan:read')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'metrics:read'));


-- ngroup
INSERT INTO ngroup (id, short_name, long_name) VALUES ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 'GHRC', 'GHRC DAAC');
INSERT INTO ngroup (id, short_name, long_name) VALUES ('f2c806ff-0362-41c8-b67e-1c589ef5b728', 'EDPub', 'Earthdata Pub');
INSERT INTO ngroup (id, short_name, long_name) VALUES
('0259fb55-1146-4461-ade2-57504e0c3ace', 'ESDIS Security', 'ESDIS Security');

-- Cueuser

-- SIT - NVD0831b3b0-b071-70ca-9c91-7c0994e79aaf
-- UAT -NVD981113a0-10a1-7074-c03e-101f675adb46
--SIT-key -NVD225b4a2a-2367-447b-b2e1-3e5b537fa962
--UAT-key -NVD6259ccb9-a4a3-4136-9822-56d87988d24b
-- INSERT INTO cueuser (id, email, name, cueusername)
--     VALUES ('225b4a2a-2367-447b-b2e1-3e5b537fa962', 'ns0066@uah.edu', 'Navaneeth Selvaraj', 'nselvaraj');

-- INSERT INTO cueuser_role (cueuser_id, role_id)
--     VALUES ('225b4a2a-2367-447b-b2e1-3e5b537fa962', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');
-- INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
--    VALUES ('225b4a2a-2367-447b-b2e1-3e5b537fa962', 'f47ac10b-58cc-4372-a567-0e02b2c3d479');


INSERT INTO cueuser (id, email, name, cueusername)
    VALUES ('6259ccb9-a4a3-4136-9822-56d87988d24b', 'navaneeth.rangaswamyselvaraj@nasa.gov', 'Navaneeth Rangaswamy Selvaraj', 'nrangasw');
INSERT INTO cueuser_role (cueuser_id, role_id)
    VALUES ('6259ccb9-a4a3-4136-9822-56d87988d24b', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
   VALUES ('6259ccb9-a4a3-4136-9822-56d87988d24b', 'f47ac10b-58cc-4372-a567-0e02b2c3d479');

INSERT INTO user_application (user_id, email, name, username, status, ngroup_id, justification, account_type)
    VALUES (
        '6259ccb9-a4a3-4136-9822-56d87988d24b',
        'navaneeth.rangaswamyselvaraj@nasa.gov',
        'Navaneeth Rangaswamy Selvaraj',
        'nrangasw',
        'approved', -- Set the status to 'approved'
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        'Initial seed administrator account.',
        'daac'
    );


-- Janani's account
INSERT INTO cueuser (id, email, name, cueusername)
    VALUES ('905dc83f-3edd-485f-9f09-ab916edf75f2', 'janani.rangaraj@nasa.gov', 'Janani Rangaraj', 'jrangara');
INSERT INTO cueuser_role (cueuser_id, role_id)
    VALUES ('905dc83f-3edd-485f-9f09-ab916edf75f2', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
   VALUES ('905dc83f-3edd-485f-9f09-ab916edf75f2', 'f47ac10b-58cc-4372-a567-0e02b2c3d479');


-- Jerrold's User
INSERT INTO cueuser (id, email, name, cueusername)
    VALUES ('98119390-40d1-70ef-0b6d-5e6c44294045', 'fake2@email.com', 'Jerrold Williams', 'jwilliams');
INSERT INTO cueuser_role (cueuser_id, role_id)
    VALUES ('98119390-40d1-70ef-0b6d-5e6c44294045', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');
INSERT INTO cueuser_auth (id, refresh_token)
   VALUES ('98119390-40d1-70ef-0b6d-5e6c44294045', '123');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
   VALUES ('98119390-40d1-70ef-0b6d-5e6c44294045', 'f47ac10b-58cc-4372-a567-0e02b2c3d479');



-- Provider
INSERT INTO provider (id, ngroup_id, short_name, long_name, can_upload, point_of_contact)
    VALUES (
        'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        'demo_provider',
        'Demo Provider',
        TRUE,
        '6259ccb9-a4a3-4136-9822-56d87988d24b'
    );

-- Egress
INSERT INTO egress (id, type, path, config, ngroup_id)
    VALUES (
        'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
        's3',
        's3://ghrc-bucket',
        '{"bucket": "ghrc-bucket", "region": "us-east-1"}',
        'f47ac10b-58cc-4372-a567-0e02b2c3d479'
    );

-- Collection
INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
    VALUES (
        'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f',
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
        'demo_collection',
        'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
        TRUE
    );
