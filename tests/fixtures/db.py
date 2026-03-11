import pytest_asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
from app.v2.database_util.db_util import get_connection_pool, setup_connection
from app.v2.type_util.egress import EgressCreate 
from app.v2.type_util.ngroup import NgroupCreate
from app.v2.type_util.auth import AuthUser
from app.v2.type_util.provider import ProviderCreate
from app.v2.type_util.egress import EgressCreate
from app.v2.type_util.collection import CollectionCreate

import uuid
import json
import asyncpg
import os

@pytest_asyncio.fixture(scope="function")
async def connection_pool():
    """Create a connection pool for the test session."""
    pool = await get_connection_pool(setup=setup_connection)
    try:
        yield pool
    finally:
        # Reset DB state 
        await reset_database(pool)
        await pool.close()

async def reset_database(pool):
    """Function to reset database after test completes."""
    # Truncate all user tables, restart sequences, and cascade to dependents.
    # Excludes system schemas.
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema NOT IN ('pg_catalog', 'information_schema')
        """)
        # tables to preserve between tests
        preserve_tables = [] 
        # Exclude migration bookkeeping tables if present
        table_idents = [
            f'{r["table_schema"]}."{r["table_name"]}"'
            for r in rows
            if r["table_name"] not in preserve_tables
        ]

        if table_idents:
            tables_csv = ", ".join(table_idents)
            # RESTART IDENTITY resets sequences; CASCADE handles FKs
            await conn.execute(f"TRUNCATE {tables_csv} RESTART IDENTITY CASCADE")

@pytest_asyncio.fixture(scope="function")
async def db_connection(connection_pool):
    """Get a connection from the pool for each test."""
    async with connection_pool.acquire() as conn:
        yield conn

# --- seed data fixtures ---
# privilege
@pytest_asyncio.fixture(scope='function')
async def seed_privileges(connection_pool):
    """Fixture for seeding database with privileges."""
    async with connection_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO privilege (id, privilege) VALUES
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
                ('a1a1a1a1-0000-0000-0000-000000000044', 'api-key:delete'),
                ('a1a1a1a1-0000-0000-0000-000000000046', 'collection:page');
            """
        )

# Roles
@pytest_asyncio.fixture(scope='function')
async def seed_roles(connection_pool):
    """Fixture for seeding database with roles."""
    async with connection_pool.acquire() as conn:
        await conn.execute(
        """INSERT INTO role (id, short_name, long_name) VALUES
            ('c924d0d3-55af-49f3-bec1-d7fd4ed475e2', 'admin', 'Admin'),
            ('39677929-ba9b-426d-8c18-f607d669fcce', 'security', 'Security'),
            ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', 'daac_manager', 'DAAC Manager'),
            ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', 'daac_staff', 'DAAC Staff'),
            ('2068cc53-1232-4bc7-9647-3e29e6418e21', 'daac_observer', 'DAAC Observer'),
            ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', 'provider', 'Provider');
        """
    )

# Role to Privilege Mappings
@pytest_asyncio.fixture(scope='function', autouse=True)
async def seed_role_privilege_mapping(seed_privileges, seed_roles, connection_pool):
    """Fixture for seeding database with role-privilege mapping."""
    async with connection_pool.acquire() as conn:
        ## Admin (has all privileges)
        await conn.execute("INSERT INTO role_privilege (role_id, privilege_id) SELECT 'c924d0d3-55af-49f3-bec1-d7fd4ed475e2', id FROM privilege;")

        ## Security
        await conn.execute(
            """INSERT INTO role_privilege (role_id, privilege_id) VALUES
                 ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:read')),
                 ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'user:page')),
                 ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'provider:read')),
                 ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'provider:update')),
                 ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'provider:delete')),
                 ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'collection:read')),
                 ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'collection:update')),
                 ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'collection:delete')),
                 ('39677929-ba9b-426d-8c18-f607d669fcce', (SELECT id from privilege where privilege = 'collection:page')),
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
            """
        )

        ## DAAC Manager
        await conn.execute(
            """INSERT INTO role_privilege (role_id, privilege_id) VALUES
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
                ('ef872fe7-92b9-45ec-ac19-80f4c478fd36', (SELECT id from privilege where privilege = 'collection:page')),
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
            """
        )

        ## DAAC Staff
        await conn.execute(
            """INSERT INTO role_privilege (role_id, privilege_id) VALUES
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'user:read')),
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:create')),
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:read')),
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:update')),
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'provider:delete')),
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'collection:create')),
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'collection:read')),
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'collection:update')),
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'collection:delete')),
                ('a8b3757b-dcf9-4943-8f64-5adaf17a17fe', (SELECT id from privilege where privilege = 'collection:page')),
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
            """
        )

        ## DAAC Observer
        await conn.execute(
            """INSERT INTO role_privilege (role_id, privilege_id) VALUES
                ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'user:read')),
                ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'provider:read')),
                ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'collection:read')),
                ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'collection:page')),
                ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'egress:read')),
                ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'file:read')),
                ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'scan:read')),
                ('2068cc53-1232-4bc7-9647-3e29e6418e21', (SELECT id from privilege where privilege = 'metrics:read'));
            """
            )

        ## Provider
        await conn.execute(
            """INSERT INTO role_privilege (role_id, privilege_id) VALUES
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'user:read')),
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'provider:read')),
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'file:upload')),
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'file:read')),
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'scan:read')),
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'metrics:read')),
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'api-key:create')),
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'api-key:read')),
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'api-key:delete')),
                ('0e686dba-e5b2-4302-aea0-e9ed0caff7d3', (SELECT id from privilege where privilege = 'collection:read'));
            """
        )
# Fixture factories to seed db 

@pytest_asyncio.fixture()
def seed_ngroup(connection_pool):
    """Factory fixture for seeding database with ngroups."""
    async def _seed_ngroup(ngroup_id, short_name, long_name):
        async with connection_pool.acquire() as conn:
            return await conn.fetchrow("INSERT INTO ngroup (id, short_name, long_name) VALUES ($1, $2, $3) RETURNING *;",

                *(ngroup_id, short_name, long_name)
            )
    return _seed_ngroup

@pytest_asyncio.fixture()
def seed_user(test_ngroup_id, connection_pool):
    """Factory fixture for seeding database with users."""
    async def _seed_user(user_id, email, cueusername, name, role_id, ngroup_id=test_ngroup_id, justification="testing", account_type="daac"):
        async with connection_pool.acquire() as conn:
            # cueuser
            await conn.execute("INSERT INTO cueuser (id, email, name, cueusername) VALUES ($1, $2, $3, $4)", *(user_id, email, name, cueusername))
            # cueuser_role
            await conn.execute("INSERT INTO cueuser_role (cueuser_id, role_id) VALUES ($1, $2)", *(user_id, role_id))
            # cueuser_ngroup
            await conn.execute("INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id) VALUES ($1, $2)", *(user_id, ngroup_id))
            # user_application
            await conn.execute("INSERT INTO user_application (user_id, email, name, username, ngroup_id, justification, account_type) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                                *(user_id, email, name, 'approved', test_ngroup_id, justification, account_type ))
    return _seed_user

@pytest_asyncio.fixture()
def seed_provider(test_ngroup_id, connection_pool):
    """Factory fixture for seeding database with providers."""
    async def _seed_provider(short_name, long_name, can_upload, point_of_contact, reason="", ngroup_id=test_ngroup_id):
        async with connection_pool.acquire() as conn:
            provider_db_record = await conn.fetchrow("INSERT INTO provider (ngroup_id, short_name, long_name, can_upload, point_of_contact, reason) VALUES ($1, $2, $3, $4, $5,$6) RETURNING *;",
                                *(ngroup_id, short_name, long_name, can_upload, point_of_contact, reason))
        return provider_db_record
    return _seed_provider

@pytest_asyncio.fixture()
def seed_egress(test_ngroup_id, connection_pool):
    """Factory fixture for seeding database with egresses."""
    async def _seed_egress(type, path, config, ngroup_id=test_ngroup_id):
        async with connection_pool.acquire() as conn:
            egress_db_record = await conn.fetchrow("INSERT INTO egress (type, path, config, ngroup_id) VALUES ($1, $2, $3::jsonb, $4) RETURNING *;",
                            *(type, path, json.dumps(config), ngroup_id))
            return egress_db_record
    return _seed_egress

@pytest_asyncio.fixture()
def seed_collection(test_ngroup_id, test_egress, test_provider, connection_pool):
    """Factory fixture for seeding database with collections."""
    async def _seed_collection(short_name, active, provider_id=test_provider["id"], egress_id=test_egress["id"], ngroup_id=test_ngroup_id):
        async with connection_pool.acquire() as conn:
            collection_db_record = await conn.fetchrow("INSERT INTO collection (ngroup_id, egress_id, short_name, provider_id, active) VALUES ($1, $2, $3, $4, $5) RETURNING id, ngroup_id, egress_id, short_name, provider_id, active",
                                            *(ngroup_id, egress_id, short_name, provider_id, active)) 
        return collection_db_record
    return _seed_collection

@pytest_asyncio.fixture()
def seed_file(test_collection, connection_pool):
    """Factory fixture for seeding database with files."""
    async def _seed_file(id, name, type, cueuser_uploaded, size_bytes,
                   collection_id=test_collection["id"], collection_path=None,
                   checksum="mock_checksum", status="unscanned",
                   upload_time=datetime.now(tz=timezone.utc),
                   scan_start=None, scan_end=None,
                   egress_start=None, scan_results=None,
                   notification_sent_at=None):
        file_db = {}
        async with connection_pool.acquire() as conn:
            file_db["file"] = await conn.fetchrow("INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, checksum, collection_path) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING * ;",
                         *(id, name, type, cueuser_uploaded, size_bytes, collection_id, checksum, collection_path))
            file_db["file_status"] = await conn.fetchrow("INSERT INTO file_status (id, status, upload_time, scan_start, scan_end, egress_start, scan_results, notification_sent_at) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8) RETURNING * ;",
                         *(id, status, upload_time, scan_start, scan_end, egress_start, scan_results, notification_sent_at))
        return file_db
    return _seed_file

@pytest_asyncio.fixture()
def seed_test_files(test_collection, seed_file):
    """Factory Fixture for bulk file seeding."""
    async def _seed_test_files(uploader_id:uuid.UUID, status_counts:Optional[Dict[str,int]]=None, collection_id:uuid.UUID=test_collection["id"], upload_offset:int=0):
        status_counts = status_counts if status_counts else {"unscanned":2, "infected": 2, "clean": 2, "distributed": 2, "scan_failed": 2}
        total_files = sum([count for _, count in status_counts.items()])
        file_size = 1024
        total_volume = total_files * file_size
        file_ids = []
        date_format = "%Y-%m-%dT%I:%M:%S%fZ"
        for status, count in status_counts.items():
            for i in range(count):
                upload_time = datetime.now(tz=timezone.utc) - timedelta(days=upload_offset)
                scan_start = upload_time + timedelta(milliseconds=5)
                scan_end = scan_start + timedelta(milliseconds=random.randint(10,30))
                file_name = f"{status}_file_{i+1}_{upload_time.date()}"
                file_id = uuid.uuid4()
                if status == "unscanned":
                    await seed_file(file_id, f"unscanned_file{i+1}", "application/octet-stream", uploader_id, file_size, collection_id=collection_id, status=status, upload_time=upload_time)
                elif status == "infected":
                    scan_results = json.dumps([{"result":"Infected", "virusName":["EICAR-AV-TEST"], "message":["eicar.com"], "dateScanned":scan_end.strftime(date_format), "engine":"Sophos"}])
                    await seed_file(file_id, file_name , "application/octet-stream", uploader_id, file_size, collection_id=collection_id, status=status, upload_time=upload_time, scan_start=scan_start, scan_end=scan_end, scan_results=scan_results)
                elif status == "clean" or status == "distributed":
                    scan_results = json.dumps([{"result":"Clean", "virusName":[], "message":[], "dateScanned":scan_end.strftime(date_format), "engine":"Sophos"}])
                    egress_start = None
                    if status == "distributed": 
                        egress_start = scan_end + timedelta(seconds=random.randint(2,5))
                    await seed_file(file_id, file_name , "application/octet-stream", uploader_id, file_size, collection_id=collection_id, status=status, upload_time=upload_time, scan_start=scan_start, scan_end=scan_end, scan_results=scan_results, egress_start=egress_start)
                else: # status == "scan_failed":
                    scan_results = json.dumps([{"result":"scan_failed", "virusName":[], "message":["mock_scan_failed"], "dateScanned":scan_end.strftime(date_format), "engine":"Sophos"}])
                    await seed_file(file_id, file_name , "application/octet-stream", uploader_id, file_size, collection_id=collection_id, status=status, upload_time=upload_time, scan_start=scan_start, scan_end=scan_end, scan_results=scan_results)
                file_ids.append(file_id)

        seed_file_details = {"total_count":total_files, "total_volume": total_volume, "status_counts": status_counts, "file_ids": file_ids}
        return seed_file_details
    return _seed_test_files

# Fixtures to seed generic test data

@pytest_asyncio.fixture(scope="function")
async def test_ngroup_id(seed_ngroup):
    """Create a test ngroup and return its ID."""
    ngroup_id = uuid.uuid4()

    await seed_ngroup(ngroup_id, "test_group", "Test Group")
    yield ngroup_id

@pytest_asyncio.fixture(scope='function')
async def test_admin_user(test_ngroup_id, seed_user):
    """Fixture to create default admin user for testing."""
    user = AuthUser(id=uuid.uuid4(), email="test_admin_user@test.com", 
                    cueusername="test_admin_user", name="test user admin",
                    roles=["admin"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))
    await seed_user(user.id, user.email, user.cueusername, user.name, "c924d0d3-55af-49f3-bec1-d7fd4ed475e2")
    yield user

@pytest_asyncio.fixture(scope='function')
async def test_daac_manager_user(test_ngroup_id, seed_user):
    """Fixture to create default daac manager user for testing."""
    user = AuthUser(id=uuid.uuid4(), email="test_daac_manager_user@test.com", 
                    cueusername="test_daac_manager_user", name="test user daac manager",
                    roles=["daac_manager"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))
    await seed_user(user.id, user.email, user.cueusername, user.name, "ef872fe7-92b9-45ec-ac19-80f4c478fd36")
    yield user

@pytest_asyncio.fixture(scope='function')
async def test_security_user(test_ngroup_id, seed_user):
    """Fixture to create default security user for testing."""
    user = AuthUser(id=uuid.uuid4(), email="test_security_user@test.com", 
                    cueusername="test_security_user", name="test user security",
                    roles=["security"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))
    await seed_user(user.id, user.email, user.cueusername, user.name, "39677929-ba9b-426d-8c18-f607d669fcce")
    yield user

@pytest_asyncio.fixture(scope='function')
async def test_daac_staff_user(test_ngroup_id, seed_user):
    """Fixture to create default daac staff user for testing."""
    user = AuthUser(id=uuid.uuid4(), email="test_daac_staff_user@test.com", 
                    cueusername="test_daac_staff_user", name="test user daac staff",
                    roles=["daac_staff"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))
    await seed_user(user.id, user.email, user.cueusername, user.name, "a8b3757b-dcf9-4943-8f64-5adaf17a17fe")
    yield user

@pytest_asyncio.fixture(scope='function')
async def test_daac_observer_user(test_ngroup_id, seed_user):
    """Fixture to create default daac observer user for testing."""
    user = AuthUser(id=uuid.uuid4(), email="test_daac_observer_user@test.com", 
                    cueusername="test_daac_observer_user", name="test user observer",
                    roles=["daac_observer"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))
    await seed_user(user.id, user.email, user.cueusername, user.name, "2068cc53-1232-4bc7-9647-3e29e6418e21")
    yield user

@pytest_asyncio.fixture(scope='function')
async def test_provider_user(test_ngroup_id, seed_user):
    """Fixture to create default provider user for testing."""
    user = AuthUser(id=uuid.uuid4(), email="test_provider_user@test.com", 
                    cueusername="test_provider_user", name="test user provider",
                    roles=["provider"], ngroups=[str(test_ngroup_id)],
                    active_ngroup_id=str(test_ngroup_id))
    await seed_user(user.id, user.email, user.cueusername, user.name, "0e686dba-e5b2-4302-aea0-e9ed0caff7d3")
    yield user

@pytest_asyncio.fixture(scope='function')
async def test_provider(test_ngroup_id, test_admin_user, seed_provider):
    """Fixture to create default provider for testing."""
    provider = ProviderCreate(short_name="test_provider",
                              long_name="Test Provider",
                              can_upload=True,
                              ngroup_id=test_ngroup_id,
                              point_of_contact=test_admin_user.id)
    provider_db_record = await seed_provider(provider.short_name, provider.long_name, provider.can_upload, provider.point_of_contact)
    yield provider_db_record

@pytest_asyncio.fixture(scope='function')
async def test_egress(test_ngroup_id, seed_egress):
    """Fixture to create  default egress for testing."""
    egress = EgressCreate(type="s3",
                            path="/data",
                            config={"destination_path":"/data/new_data", "bucket":"mock_s3_dest_bucket"})
    egress_db_record = await seed_egress(egress.type, egress.path, egress.config, ngroup_id=test_ngroup_id)
    yield egress_db_record

@pytest_asyncio.fixture(scope='function')
async def test_collection(test_egress, test_provider, seed_collection):
    """Fixture to create default collection for testing."""
    collection = CollectionCreate(short_name="test_collection",
                                  active=True,
                                  provider_id=test_provider["id"],
                                  egress_id=test_egress["id"])
    collection_db_record = await seed_collection(collection.short_name, collection.active)
    yield collection_db_record

@pytest_asyncio.fixture(scope="function")
async def get_database_pool():
    """Fixture used to replace database_pool in lambda handler tests."""
    db_pool = await asyncpg.create_pool(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT", 5432),
        database=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASS"),
        ssl=os.getenv("DB_SSL_MODE", "require"),
        min_size=1,
        max_size=3,
        timeout=8
    )
    try:
        yield db_pool
    finally:
        await db_pool.close()

