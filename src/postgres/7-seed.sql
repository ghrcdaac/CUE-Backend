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
INSERT INTO cueuser (id, email, name, cueusername)
    VALUES ('2821d300-70a1-7009-73ce-d832bf01cb4e', 'fake@email.com', 'Davis Gaunt', 'dgaunt_local');
INSERT INTO cueuser_role (cueuser_id, role_id)
    VALUES ('2821d300-70a1-7009-73ce-d832bf01cb4e', 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2');
INSERT INTO cueuser_auth (id, refresh_token)
    VALUES ('2821d300-70a1-7009-73ce-d832bf01cb4e', '123');
INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
    VALUES ('2821d300-70a1-7009-73ce-d832bf01cb4e', 'f47ac10b-58cc-4372-a567-0e02b2c3d479');



INSERT INTO cueuser (id, email, name, cueusername)
    VALUES ('0831b3b0-b071-70ca-9c91-7c0994e79aaf', 'ns0066@uah.edu', 'Navaneeth Selvaraj', 'nselvaraj');
INSERT INTO cueuser_auth (id,refresh_token)
    VALUES ('0831b3b0-b071-70ca-9c91-7c0994e79aaf', '123');

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
        '2821d300-70a1-7009-73ce-d832bf01cb4e'
    );

INSERT INTO provider (id, ngroup_id, short_name, long_name, can_upload, point_of_contact)
    VALUES (
        '3446a76a-e159-47ad-b57c-949162ba1171',
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        'demo_provider1',
        'Demo Provider1',
        TRUE,
        '2821d300-70a1-7009-73ce-d832bf01cb4e'
    );

INSERT INTO provider (id, ngroup_id, short_name, long_name, can_upload, point_of_contact)
    VALUES (
        '00b29199-d6b0-42fc-bc2c-f434a5735941',
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        'demo_provider2',
        'Demo Provider2',
        TRUE,
        '2821d300-70a1-7009-73ce-d832bf01cb4e'
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

INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
    VALUES (
        'ceb53f22-bbe1-416d-9859-e50444a5cac6',
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
        'demo_collection1',
        '3446a76a-e159-47ad-b57c-949162ba1171',
        TRUE
    );

INSERT INTO collection (id, ngroup_id, egress_id, short_name, provider_id, active)
    VALUES (
        '742c9bd9-70ed-43ff-9013-e7443c861672',
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        'f8c2b6e3-d5b4-4e7a-8c1f-2a4d9e6b7c3a',
        'demo_collection2',
        '00b29199-d6b0-42fc-bc2c-f434a5735941',
        TRUE
    );

-- File
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('73f10a44-facc-44fc-8a33-51a644aa0951', 'test1.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('6f13ccf6-44fe-4783-bd92-9c4bace37b5b', 'test2.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('e562bd9a-e470-4a41-b395-8f89d352327e', 'test3.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'a7e2f4c8-5d9b-4e6a-8c1f-2b4d9e7a6c3f', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('d1f55793-7251-4aeb-9f42-880401251dc0', 'test4.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'ceb53f22-bbe1-416d-9859-e50444a5cac6', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('9d1c9acd-0e04-4bed-a3a2-e833aeef5e30', 'test5.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'ceb53f22-bbe1-416d-9859-e50444a5cac6', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('d4370fc3-4da2-4a87-823d-a326cfc62a09', 'test6.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'ceb53f22-bbe1-416d-9859-e50444a5cac6', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('61d75f20-e5f7-4f1d-8262-6fefe4027a1a', 'test7.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'ceb53f22-bbe1-416d-9859-e50444a5cac6', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('d4995ea4-1ccd-4304-85ba-4f8b794c328e', 'test8.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'ceb53f22-bbe1-416d-9859-e50444a5cac6', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('8eea83ec-b3e5-4c06-9502-fa68bcb65e57', 'test9.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'ceb53f22-bbe1-416d-9859-e50444a5cac6', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('5c3be2ac-ba5d-43e0-946e-c3d1f022de3f', 'test10.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'ceb53f22-bbe1-416d-9859-e50444a5cac6', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('362818f0-33c0-451c-a0c8-1ce86b2ed25d', 'test11.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'ceb53f22-bbe1-416d-9859-e50444a5cac6', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('a810cef3-a546-4d73-a498-2546c4fcb030', 'test12.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, 'ceb53f22-bbe1-416d-9859-e50444a5cac6', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('35db0a6c-f217-4868-bc66-1044714ac464', 'test13.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, '742c9bd9-70ed-43ff-9013-e7443c861672', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('c781c13e-2134-497f-ae77-88f777e51b2a', 'test14.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, '742c9bd9-70ed-43ff-9013-e7443c861672', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('952af961-33c8-4b7d-a109-76afb58f9d0f', 'test15.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, '742c9bd9-70ed-43ff-9013-e7443c861672', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');
INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
    VALUES ('97e55a2d-0662-4ea0-a93d-b4872e65cf61', 'test16.csv', 'text/csv', '98119390-40d1-70ef-0b6d-5e6c44294045', 161, '742c9bd9-70ed-43ff-9013-e7443c861672', false, 'tZTyivqvZXLKFJf17r3CxxD92w3G6yuA+i1Dn7/Dmms=');

--File Status
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('73f10a44-facc-44fc-8a33-51a644aa0951', '2025-05-16 16:06:42.040007+00', '2025-05-16 18:41:37', '2025-05-16 18:45:37', NULL, 'clean', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('6f13ccf6-44fe-4783-bd92-9c4bace37b5b', '2025-05-16 16:06:43.172934+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('e562bd9a-e470-4a41-b395-8f89d352327e', '2025-05-16 16:06:45.267025+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('d1f55793-7251-4aeb-9f42-880401251dc0', '2025-05-16 16:06:49.353004+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('9d1c9acd-0e04-4bed-a3a2-e833aeef5e30', '2025-05-16 16:09:33.858927+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('d4370fc3-4da2-4a87-823d-a326cfc62a09', '2025-05-16 16:09:34.972482+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('61d75f20-e5f7-4f1d-8262-6fefe4027a1a', '2025-05-16 16:09:37.072337+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('d4995ea4-1ccd-4304-85ba-4f8b794c328e', '2025-05-16 16:09:41.165691+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('8eea83ec-b3e5-4c06-9502-fa68bcb65e57', '2025-05-16 16:13:41.948884+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('5c3be2ac-ba5d-43e0-946e-c3d1f022de3f', '2025-05-16 16:13:43.045816+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('362818f0-33c0-451c-a0c8-1ce86b2ed25d', '2025-05-16 16:13:45.125014+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('a810cef3-a546-4d73-a498-2546c4fcb030', '2025-05-16 16:13:49.213534+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('35db0a6c-f217-4868-bc66-1044714ac464', '2025-05-16 16:19:42.197763+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('c781c13e-2134-497f-ae77-88f777e51b2a', '2025-05-16 16:19:43.296427+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('952af961-33c8-4b7d-a109-76afb58f9d0f', '2025-05-16 16:19:45.389141+00', NULL, NULL, NULL, 'unscanned', NULL);
INSERT INTO file_status (id, upload_time, scan_start, scan_end, egress_start, status, scan_results)
    VALUES ('97e55a2d-0662-4ea0-a93d-b4872e65cf61', '2025-05-16 16:19:49.484342+00', NULL, NULL, NULL, 'unscanned', NULL);
