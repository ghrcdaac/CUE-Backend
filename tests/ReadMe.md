# Tests

This directory contains the unit and integration tests for the CUE backend application. Tests are written with **pytest** and **pytest-asyncio**, and run against a **dedicated test PostgreSQL database**. External services (AWS via boto3, and Keycloak via httpx) are mocked.

---

## Test structure

### `unit_tests/`
Unit tests focus on isolated functions and logic.

- `unit_tests/api_utils_unit_tests/`  
  Unit tests for the v2 utility functions (code under `src/python/api/v2`).

- `unit_tests/event_lambda_unit_tests/`  
  Unit tests for event lambda “logic” functions (code under `src/python/event_lambdas`).

- `unit_tests/.coveragerc`  
  Coverage configuration for unit tests (primarily used to omit files from coverage).

---

### `integration_tests/`
Integration tests validate the behavior of API endpoints and lambda handlers end-to-end.

- `integration_tests/api_utils_integration_tests/`  
  Integration tests for API endpoints.

- `integration_tests/event_lambda_handler_tests/`  
  Integration tests for event lambda **async handler** functions.

- `integration_tests/.coveragerc`  
  Coverage configuration for integration tests (primarily used to omit files from coverage).

---

### `fixtures/`
Shared fixtures used across tests.

- `fixtures/db.py`  
  Fixtures for:
  - creating the database connection
  - creating common test records
  - seeding additional data

  **Important:** `seed_role_privilege_mapping` is an `autouse` fixture (runs for all tests).  
  If you add/change roles or privileges, update this fixture accordingly.

- Other files in `fixtures/`  
  Factory fixtures for creating objects that depend on other objects.  

---

### `conftest.py`
Common pytest fixtures used across tests, and the entry point that imports fixtures from `fixtures/`.

This is where fixtures for mocking external interactions live (boto3 client and Keycloak API).

---

## Prerequisites

- **Docker** installed and running
- **Docker Compose** installed
- A dedicated **PostgreSQL test database** configured in `.env`
  - configure name/user/password/host/port for the test DB
  - see `src/postgres/setup-test-db.sh` for how the test DB is prepared

---

## Running tests

### 1) Build and start containers

```bash
docker compose up --build -d
```

### 2) Run tests inside the Docker container

`tests/run_test.sh` is the recommended entry point. It wraps the pytest commands for unit and integration tests.

Optional: add `-s` to the underlying pytest command if you want to display logs / print statements.

#### Unit tests

```bash
tests/run_test.sh --unit
```

Equivalent raw pytest command:

```bash
pytest -v \
  --cov=v2 --cov=event_lambdas \
  --cov-config=tests/unit_tests/.coveragerc \
  --cov-report=term-missing --cov-append \
  tests/unit_tests/
```

#### Integration tests

```bash
tests/run_test.sh --integration
```

Equivalent raw pytest command:

```bash
pytest -v \
  --cov=v2 --cov=event_lambdas \
  --cov-config=tests/integration_tests/.coveragerc \
  --cov-report=term-missing --cov-append \
  tests/integration_tests/
```

#### All tests

```bash
tests/run_test.sh --all
```

---

## Notes / behavior

- Current tests primarily cover:
  - `src/python/api/v2`
  - `src/python/event_lambdas`
- The test suite uses a **separate test database** to avoid interfering with development/production data.
- The test database is reset between tests, ensuring tests run in isolation.
- `conftest.py` sets up the test environment, mocks external interactions, and serves as the import/aggregation point for fixtures in `fixtures/`.
- Make sure to update `TEST_NGROUP_ID` in `conftest.py` if your test setup requires a different value.
- AWS and Keycloak interactions are mocked:
  - boto3 is patched with mock client so tests do not call AWS
  - Keycloak requests are mocked via httpx transport
- Async tests and fixtures run on an asyncio event loop managed by **pytest-asyncio**.

---

## Adding new tests

Add tests alongside existing ones and follow naming conventions:

- **Unit tests (utils):**
  - add to an existing file such as `test_utils_ngroup.py`, `test_utils_upload.py`
  - or create `test_utils_<name>.py`

- **Unit tests (lambda logic):**
  - add to an existing file such as `test_logic_infected_logger.py`, `test_logic_file_transfer.py`
  - or create `test_logic_<name>.py`

- **Integration tests (API endpoints):**
  - add to an existing file such as `test_endpoints_ngroup.py`, `test_endpoint_upload.py`
  - or create `test_endpoint_<name>.py`

- **Integration tests (lambda handlers):**
  - add to an existing file such as `test_handler_infected_logger.py`, `test_handler_file_transfer.py`
  - or create `test_handler_<lambda_name>.py`

### Async / import-time guidance

- For modules that execute code at import time: **import inside the test** rather than at the top of the file.
- Do not create or close event loops manually. Let `pytest-asyncio` manage the loop to avoid loop-related errors.
- For lambda modules that touch the event loop:
  - patch code that modifies the loop so tests don’t mutate loop state
  - use `patch_loop` to patch `asyncio.get_running_loop` and prevent loop creation during module import
- Patch `get_database_pool` to return the `get_database_pool` fixture (so the DB pool is not treated as a global singleton in tests).

---

## Fixtures

### Test fixtures (`test_*`)
Fixtures starting with `test_` (in `fixtures/db.py`) provide convenient defaults for common entities:
- ngroup, provider, collection, egress, and user roles

Example:
- `test_admin_user` inserts an admin user belonging to `test_ngroup_id` and returns an `AuthUser`.
- `test_collection` inserts a collection using defaults from `test_ngroup_id`, `test_egress`, and `test_provider`.

### Seed fixtures (`seed_*`)
Fixtures starting with `seed_` insert records into the database.

- Some `seed_*` fixtures populate base authorization data (roles, privileges, role-privilege mappings).
- Others behave like “insert factories”: they insert new records using defaults (coming from `test_*` fixtures), but allow overriding via keyword args.

Example:

- `seed_collection(short_name, active, provider_id=test_provider["id"], egress_id=test_egress["id"], ngroup_id=test_ngroup_id)`

You can call it with defaults:

```python
new_collection = await seed_collection("new_collection", True)
```

Or override dependencies by creating new related records first:

```python
new_ngroup = await seed_ngroup(new_ngroup_id, "new_ngroup", "New Ngroup")
new_egress = await seed_egress("s3", "/data", {"destination_path": "/sub_folder"}, new_ngroup["id"])
new_provider = await seed_provider(
    "new_ngroup_provider",
    "New Ngroup Provider",
    True,
    test_admin_user.id,
    ngroup_id=new_ngroup["id"],
)
new_collection = await seed_collection(
    "new_collection",
    True,
    provider_id=new_provider["id"],
    egress_id=new_egress["id"],
    ngroup_id=new_ngroup["id"],
)
```

### Make fixtures (`make_*`)
Fixtures starting with `make_` (in `fixtures/`) build complex objects.

---

## Fixtures that mock external interactions (in `conftest.py`)

- `mock_boto3_client`  
  Mocks AWS interactions by patching `boto3.client` globally.

- `patch_async_client`  
  Mocks Keycloak interactions using `httpx.MockTransport` and patches `httpx.AsyncClient` globally.