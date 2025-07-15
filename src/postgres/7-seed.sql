-- Privileges
INSERT INTO privilege (privilege) VALUES ('admin');
INSERT INTO privilege (privilege) VALUES ('create_user');
INSERT INTO privilege (privilege) VALUES ('approve_user');
INSERT INTO privilege (privilege) VALUES ('assign_role');
INSERT INTO privilege (privilege) VALUES ('assign_ngroup');
INSERT INTO privilege (privilege) VALUES ('create_provider');
INSERT INTO privilege (privilege) VALUES ('manage_provider');
INSERT INTO privilege (privilege) VALUES ('view_provider');
INSERT INTO privilege (privilege) VALUES ('suspend_provider');
INSERT INTO privilege (privilege) VALUES ('reinstat_provider');
INSERT INTO privilege (privilege) VALUES ('security_reinstate');
INSERT INTO privilege (privilege) VALUES ('manage_collection');
INSERT INTO privilege (privilege) VALUES ('view_collection');
INSERT INTO privilege (privilege) VALUES ('manage_egress');
INSERT INTO privilege (privilege) VALUES ('view_egress');
INSERT INTO privilege (privilege) VALUES ('upload');
INSERT INTO privilege (privilege) VALUES ('view_files');
INSERT INTO privilege (privilege) VALUES ('view_scan_results');
INSERT INTO privilege (privilege) VALUES ('view_all_files');
INSERT INTO privilege (privilege) VALUES ('view_all_scan');
INSERT INTO privilege (privilege) VALUES ('metrics');

-- Roles

-- Admin
INSERT INTO role (id, short_name, long_name) VALUES ('c924d0d3-55af-49f3-bec1-d7fd4ed475e2', 'admin', 'Admin');
INSERT INTO role_privilege (role_id, privilege) VALUES ('c924d0d3-55af-49f3-bec1-d7fd4ed475e2', 'admin');

-- Security
INSERT INTO role (id, short_name, long_name) VALUES ('39677929-ba9b-426d-8c18-f607d669fcce', 'security', 'Security');
INSERT INTO role_privilege (role_id, privilege) VALUES ('39677929-ba9b-426d-8c18-f607d669fcce', 'suspend_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('39677929-ba9b-426d-8c18-f607d669fcce', 'reinstat_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('39677929-ba9b-426d-8c18-f607d669fcce', 'security_reinstate');
INSERT INTO role_privilege (role_id, privilege) VALUES ('39677929-ba9b-426d-8c18-f607d669fcce', 'view_all_files');
INSERT INTO role_privilege (role_id, privilege) VALUES ('39677929-ba9b-426d-8c18-f607d669fcce', 'view_all_scan');
INSERT INTO role_privilege (role_id, privilege) VALUES ('39677929-ba9b-426d-8c18-f607d669fcce', 'metrics');

-- DAAC Manager
INSERT INTO role (id, short_name, long_name) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'daac_manager', 'DAAC Manager');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'create_user');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'approve_user');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'assign_role');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'assign_ngroup');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'create_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'manage_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'view_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'suspend_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'reinstat_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'manage_collection');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'view_collection');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'manage_egress');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'view_egress');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'upload');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'view_files');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'view_scan_results');
INSERT INTO role_privilege (role_id, privilege) VALUES ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'metrics');

-- DAAC Staff
INSERT INTO role (id, short_name, long_name) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'daac_staff', 'DAAC Staff');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'manage_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'view_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'suspend_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'reinstat_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'manage_collection');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'view_collection');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'manage_egress');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'view_egress');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'upload');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'view_files');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'view_scan_results');
INSERT INTO role_privilege (role_id, privilege) VALUES ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'metrics');

-- DAAC Observer
INSERT INTO role (id, short_name, long_name) VALUES ('2068cc53-1232-4bc7-9647-3e29e6418e21', 'daac_observer', 'DAAC Observer');
INSERT INTO role_privilege (role_id, privilege) VALUES ('2068cc53-1232-4bc7-9647-3e29e6418e21', 'view_provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('2068cc53-1232-4bc7-9647-3e29e6418e21', 'view_collection');
INSERT INTO role_privilege (role_id, privilege) VALUES ('2068cc53-1232-4bc7-9647-3e29e6418e21', 'view_egress');
INSERT INTO role_privilege (role_id, privilege) VALUES ('2068cc53-1232-4bc7-9647-3e29e6418e21', 'view_files');
INSERT INTO role_privilege (role_id, privilege) VALUES ('2068cc53-1232-4bc7-9647-3e29e6418e21', 'view_scan_results');
INSERT INTO role_privilege (role_id, privilege) VALUES ('2068cc53-1232-4bc7-9647-3e29e6418e21', 'metrics');

-- ngroup
INSERT INTO ngroup (id, short_name, long_name) VALUES ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 'GHRC', 'GHRC DAAC');

-- Provider
INSERT INTO role (id, short_name, long_name) VALUES ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', 'provider', 'Provider');
INSERT INTO role_privilege (role_id, privilege) VALUES ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', 'upload');
INSERT INTO role_privilege (role_id, privilege) VALUES ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', 'view_files');

-- Cueuser

-- SIT - NVD0831b3b0-b071-70ca-9c91-7c0994e79aaf
-- UAT -NVD981113a0-10a1-7074-c03e-101f675adb46
INSERT INTO cueuser (id, email, name, cueusername)
    VALUES ('981113a0-10a1-7074-c03e-101f675adb46', 'ns0066@uah.edu', 'Navaneeth Selvaraj', 'nselvaraj');
INSERT INTO cueuser_auth (id,refresh_token)
    VALUES ('981113a0-10a1-7074-c03e-101f675adb46', '123');

INSERT INTO cueuser_role (cueuser_id, role_id)
    VALUES ('981113a0-10a1-7074-c03e-101f675adb46', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');



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
        '981113a0-10a1-7074-c03e-101f675adb46'
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
