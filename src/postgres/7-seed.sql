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
    ('a1a1a1a1-0000-0000-0000-000000000045', 'user:page'),
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
    ('a1a1a1a1-0000-0000-0000-000000000040', 'archive:query'),
    ('a1a1a1a1-0000-0000-0000-000000000041', 'api-key:create'),
    ('a1a1a1a1-0000-0000-0000-000000000042', 'api-key:read'),
    ('a1a1a1a1-0000-0000-0000-000000000043', 'api-key:update'),
    ('a1a1a1a1-0000-0000-0000-000000000044', 'api-key:delete');

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
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:page')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'provider:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'provider:update')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'provider:delete')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'collection:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'collection:update')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'collection:delete')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'egress:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:update')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:delete')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:suspend')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:reinstate')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'role:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'file:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'scan:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'metrics:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'file:delete')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'api-key:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'api-key:update')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'api-key:delete')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'application:read')),
    ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'application:approve'));

-- DAAC Manager
INSERT INTO role_privilege (role_id, privilege_id) VALUES
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'application:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'application:approve')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:create')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:page')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:update')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:delete')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'user:assign_role')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'provider:create')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'provider:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'provider:update')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'provider:delete')),
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
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'archive:query')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'api-key:create')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'api-key:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'api-key:update')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'api-key:delete')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'role:create')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'role:read')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'role:update')),
    ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'role:delete'));

-- DAAC Staff
INSERT INTO role_privilege (role_id, privilege_id) VALUES
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'user:read')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:create')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:read')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:update')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:delete')),
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
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'archive:query')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'api-key:create')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'api-key:read')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'api-key:update')),
    ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'api-key:delete')); 

-- DAAC Observer
INSERT INTO role_privilege (role_id, privilege_id) VALUES
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'user:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'provider:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'collection:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'egress:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'file:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'scan:read')),
    ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'metrics:read'));

-- Provider
INSERT INTO role_privilege (role_id, privilege_id) VALUES
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'user:read')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'provider:read')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'file:upload')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'file:read')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'scan:read')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'metrics:read')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'api-key:create')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'api-key:read')),
    ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'api-key:delete'));


-- ngroup
INSERT INTO ngroup (id, short_name, long_name) VALUES ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 'GHRC', 'GHRC DAAC');
INSERT INTO ngroup (id, short_name, long_name) VALUES ('f2c806ff-0362-41c8-b67e-1c589ef5b728', 'EDPub', 'Earthdata Pub');
INSERT INTO ngroup (id, short_name, long_name) VALUES('0259fb55-1146-4461-ade2-57504e0c3ace', 'ESDIS Security', 'ESDIS Security');
INSERT INTO ngroup (id, short_name, long_name) VALUES ('1675f412-7468-4cd4-adb0-20b08236079b', 'CUE', 'Cloud Upload Environment');


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



--PROD
-- INSERT INTO cueuser (id, email, name, cueusername)
--     VALUES ('2333d3c9-4679-467f-baee-a6be78a0c5b6', 'navaneeth.rangaswamyselvaraj@nasa.gov', 'Navaneeth Rangaswamy Selvaraj', 'nrangasw');
-- INSERT INTO cueuser_role (cueuser_id, role_id)
--     VALUES ('2333d3c9-4679-467f-baee-a6be78a0c5b6', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');
-- INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
--    VALUES ('2333d3c9-4679-467f-baee-a6be78a0c5b6', 'f47ac10b-58cc-4372-a567-0e02b2c3d479');
-- INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
--    VALUES ('2333d3c9-4679-467f-baee-a6be78a0c5b6', 'f2c806ff-0362-41c8-b67e-1c589ef5b728');
-- INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
--    VALUES ('2333d3c9-4679-467f-baee-a6be78a0c5b6', '1675f412-7468-4cd4-adb0-20b08236079b');

-- INSERT INTO user_application (user_id, email, name, username, status, ngroup_id, justification, account_type)
--     VALUES (
--         '2333d3c9-4679-467f-baee-a6be78a0c5b6',
--         'navaneeth.rangaswamyselvaraj@nasa.gov',
--         'Navaneeth Rangaswamy Selvaraj',
--         'nrangasw',
--         'approved', -- Set the status to 'approved'
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'Initial seed administrator account.',
--         'daac'
--     );

-- UAT account
INSERT INTO cueuser (id, email, name, cueusername)
    VALUES ('6259ccb9-a4a3-4136-9822-56d87988d24b', 'navaneeth.rangaswamyselvaraj@nasa.gov', 'Navaneeth Rangaswamy Selvaraj', 'nrangasw');
INSERT INTO cueuser_role (cueuser_id, role_id)
    VALUES ('6259ccb9-a4a3-4136-9822-56d87988d24b', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
   VALUES ('6259ccb9-a4a3-4136-9822-56d87988d24b', 'f47ac10b-58cc-4372-a567-0e02b2c3d479');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
   VALUES ('6259ccb9-a4a3-4136-9822-56d87988d24b', 'f2c806ff-0362-41c8-b67e-1c589ef5b728');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
   VALUES ('6259ccb9-a4a3-4136-9822-56d87988d24b', '1675f412-7468-4cd4-adb0-20b08236079b');

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


INSERT INTO cueuser (id, email, name, cueusername)
    VALUES ('bf63f3ef-7a2b-4742-8b1f-74429c57d460', 'navaneeth026@gmail.com', 'Navaneeth R Selvaraj', 'navaneeth026@gmail.com');
INSERT INTO cueuser_role (cueuser_id, role_id)
    VALUES ('bf63f3ef-7a2b-4742-8b1f-74429c57d460', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
   VALUES ('bf63f3ef-7a2b-4742-8b1f-74429c57d460', 'f47ac10b-58cc-4372-a567-0e02b2c3d479');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
   VALUES ('bf63f3ef-7a2b-4742-8b1f-74429c57d460', 'f2c806ff-0362-41c8-b67e-1c589ef5b728');

INSERT INTO user_application (user_id, email, name, username, status, ngroup_id, justification, account_type)
    VALUES (
        'bf63f3ef-7a2b-4742-8b1f-74429c57d460',
        'navaneeth026@gmail.com',
        'Navaneeth Rangaswamy Selvaraj',
        'navaneeth026@gmail.com',
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

INSERT INTO user_application (user_id, email, name, username, status, ngroup_id, justification, account_type)
    VALUES (
        '905dc83f-3edd-485f-9f09-ab916edf75f2',
        'janani.rangaraj@nasa.gov',
        'Janani Rangaraj',
        'jrangara',
        'approved', -- Set the status to 'approved'
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        'Initial seed administrator account.',
        'daac'
    );


-- Jerrold's User
INSERT INTO cueuser (id, email, name, cueusername)
    VALUES ('5b33babe-5f98-4ff5-91d1-025681741288', 'williamsjr@ornl.gov', 'Jerrold Williams', 'jwilliams');
INSERT INTO cueuser_role (cueuser_id, role_id)
    VALUES ('5b33babe-5f98-4ff5-91d1-025681741288', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
   VALUES ('5b33babe-5f98-4ff5-91d1-025681741288', 'f47ac10b-58cc-4372-a567-0e02b2c3d479');

INSERT INTO user_application (user_id, email, name, username, status, ngroup_id, justification, account_type)
    VALUES (
        '5b33babe-5f98-4ff5-91d1-025681741288',
        'williamsjr@ornl.gov',
        'Jerrold Williams',
        'jrwill25',
        'approved', -- Set the status to 'approved'
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        'Initial seed administrator account.',
        'daac'
    );


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
        '{"bucket": "ghrc-bucket", "region": "us-west-2"}',
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

    

-- INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c4f',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data11',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c5f',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data10',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c6f',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data9',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c7f',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data8',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c8f',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data7',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c9f',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data6',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6cf1',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data5',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c1f',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data4',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c2f',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data3',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6cf4',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data2',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
--     INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
--     VALUES (
--         'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6cf5',
--         'f47ac10b-58cc-4372-a567-0e02b2c3d479',
--         'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
--         'demo_data1',
--         'd3f9c1a7-4b8e-4c6b-9a2f-1e7d5a8c9b3d',
--         TRUE
--     );
-- --File test data
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('73f10a44-facc-44fc-8a33-51a644aa0951', 'test1.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('6f13ccf6-44fe-4783-bd92-9c4bace37b5b', 'test2.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 100, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c4f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('e562bd9a-e470-4a41-b395-8f89d352327e', 'test3.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 120, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c5f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('d1f55793-7251-4aeb-9f42-880401251dc0', 'test4.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 90, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c6f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('9d1c9acd-0e04-4bed-a3a2-e833aeef5e30', 'test5.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 30, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c7f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('d4370fc3-4da2-4a87-823d-a326cfc62a09', 'test6.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 200, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c8f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('61d75f20-e5f7-4f1d-8262-6fefe4027a1a', 'test7.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 250, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c9f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('d4995ea4-1ccd-4304-85ba-4f8b794c328e', 'test8.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 3500, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c1f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('8eea83ec-b3e5-4c06-9502-fa68bcb65e57', 'test9.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 128000, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c2f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('5c3be2ac-ba5d-43e0-946e-c3d1f022de3f', 'test10.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 50000, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6cf1', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('362818f0-33c0-451c-a0c8-1ce86b2ed25d', 'test11.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 20000, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6cf4', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('a810cef3-a546-4d73-a498-2546c4fcb030', 'test12.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6cf5', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('35db0a6c-f217-4868-bc66-1044714ac464', 'test13.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('c781c13e-2134-497f-ae77-88f777e51b2a', 'test14.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('952af961-33c8-4b7d-a109-76afb58f9d0f', 'test15.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('97e55a2d-0662-4ea0-a93d-b4872e65cf61', 'test16.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
--     VALUES ('97e55a2d-0662-4ea0-a93d-b4872e65cf62', 'test17.csv', 'text/csv', '6259ccb9-a4a3-4136-9822-56d87988d24b', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
-- --File Status
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('73f10a44-facc-44fc-8a33-51a644aa0951', '2025-10-06 16:06:42.040007+00', '2025-10-06 18:41:37', '2025-10-06 18:45:37', NULL, 'clean', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
-- VALUES (
--     '6f13ccf6-44fe-4783-bd92-9c4bace37b5b',
--     '2025-10-06 16:06:43.172934+00',
--     '2025-10-06 18:41:37',
--     '2025-10-06 18:41:37',
--     NULL,
--     'infected',
--     '{"results": {"sns_arn": "arn:aws:sns:us-east-1:123456789012:example-sns-topic-name"}}'
-- );
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('e562bd9a-e470-4a41-b395-8f89d352327e', '2025-10-06 16:06:45.267025+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', NULL, 'infected', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('d1f55793-7251-4aeb-9f42-880401251dc0', '2025-10-06 16:06:49.353004+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', NULL, 'infected', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('9d1c9acd-0e04-4bed-a3a2-e833aeef5e30', '2025-10-06 16:09:33.858927+00', NULL, NULL, NULL, 'infected', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('d4370fc3-4da2-4a87-823d-a326cfc62a09', '2025-10-06 16:09:34.972482+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', NULL, 'clean', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('61d75f20-e5f7-4f1d-8262-6fefe4027a1a', '2025-10-06 16:09:37.072337+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', NULL, 'clean', '{"results": {"sns_arn": "arn:aws:sns:us-east-1:123456789012:example-sns-topic-name"}}');
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('d4995ea4-1ccd-4304-85ba-4f8b794c328e', '2025-10-06 16:09:41.165691+00', NULL, NULL, NULL, 'clean', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('8eea83ec-b3e5-4c06-9502-fa68bcb65e57', '2025-10-06 16:13:41.948884+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', NULL, 'scan_failed', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('5c3be2ac-ba5d-43e0-946e-c3d1f022de3f', '2025-10-06 16:13:43.045816+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', NULL, 'scan_failed', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('362818f0-33c0-451c-a0c8-1ce86b2ed25d', '2025-10-06 16:13:45.125014+00', NULL, NULL, NULL, 'scan_failed', '{"results": {"sns_arn": "arn:aws:sns:us-east-1:123456789012:example-sns-topic-name","virus":"Sophio"}}');
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('a810cef3-a546-4d73-a498-2546c4fcb030', '2025-10-06 16:13:49.213534+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', '2025-10-06 18:41:37', 'distributed', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('35db0a6c-f217-4868-bc66-1044714ac464', '2025-10-06 16:19:42.197763+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', '2025-10-06 18:41:37', 'distributed', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('c781c13e-2134-497f-ae77-88f777e51b2a', '2025-10-06 16:19:43.296427+00', NULL, NULL, NULL, 'distributed', '{"results": {"sns_arn": "arn:aws:sns:us-east-1:123456789012:example-sns-topic-name"}}');
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('952af961-33c8-4b7d-a109-76afb58f9d0f', '2025-10-06 16:19:45.389141+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', NULL, 'unscanned', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('97e55a2d-0662-4ea0-a93d-b4872e65cf61', '2025-10-06 16:19:49.484342+00', '2025-10-06 18:41:37', '2025-10-06 18:41:37', NULL, 'unscanned', NULL);
-- INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
--     VALUES ('97e55a2d-0662-4ea0-a93d-b4872e65cf62', '2025-10-06 16:19:49.484342+00', NULL, NULL, NULL, 'unscanned', NULL);