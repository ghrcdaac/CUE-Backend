# Tests

This directory contains the unit and integration tests for the CUE backend application.

## Test Structure

The tests are organized into the following files:

*   **`conftest.py`:** Contains Pytest fixtures that are used across multiple test files. These fixtures handle setting up the test environment, creating a connection pool, and providing mock data.
*   **`test_database_util_egress.py`:** Contains unit tests for the database utility functions in `lambda_utils/database_util/db_util.py` and the database operation functions for `egress` in `lambda_utils/database_util/egress.py`.
*   **`test_database_util_ngroup.py`:** Contains unit tests for the database operation functions for `ngroup` in `lambda_utils/database_util/ngroup.py`.
*   **`test_utils_egress.py`:** Contains integration tests for the `egress` wrapper functions in `utils/egress.py`.
*   **`test_utils_ngroup.py`:** Contains integration tests for the `ngroup` wrapper functions in `utils/ngroup.py`.

## Prerequisites

*   **Docker:** You need to have Docker installed and running on your system.
*   **Docker Compose:** You need to have Docker Compose installed.
*   **Test Database:** A dedicated PostgreSQL database for testing should be created. The database name, user, password, host, and port should be configured in the `.env` file.

## Running Tests

### Inside Docker (Recommended)

1.  **Build the Docker Image and Start Containers:**

    ```bash
    docker compose up --build -d
    ```

2.  **Run Tests:**

    ```bash
    docker compose exec api pytest -v tests/
    ```

### Locally (Without Docker)

1.  **Install Dependencies:**

    ```bash
    poetry install
    ```

2.  **Set Environment Variables:**

    Ensure that the following environment variables are set in your local environment, pointing to your **test database**:

    ```
    PG_DB_TEST=your_test_database_name
    PG_USER_TEST=your_test_database_user
    PG_PASS_TEST=your_test_database_password
    PG_HOST_TEST=localhost  # Or the hostname of your test database
    PG_PORT_TEST=5432
    TEST_NGROUP_ID=your_test_ngroup_uuid
    ```
    Also, create a test ngroup in your test database.

3.  **Run Tests:**

    ```bash
    pytest -v tests/
    ```

## Notes

*   The tests use a separate test database to avoid interfering with development or production data.
*   The `conftest.py` file sets up the test environment and provides fixtures for database connections and mock data.
*   The unit tests in `test_database_util.py` and `test_database_util_ngroup.py` primarily focus on individual database functions and may use mocking to isolate them from the actual database.
*   The integration tests in `test_utils.py` and `test_utils_ngroup.py` interact with a real database to test the end-to-end functionality of the wrapper functions.
*   The `init.sql` script in `src/postgres` now includes the creation of the test database (if it doesn't exist) and the necessary tables within the test database. Make sure to update it with any schema changes.
*   When running tests locally, ensure the `src/python` directory is in your `PYTHONPATH` environment variable so that modules can be imported correctly.
*   Make sure to update the `TEST_NGROUP_ID` in `conftest.py` if needed.

## Adding New Tests

When adding new functionality, make sure to add corresponding tests. Follow the existing structure and naming conventions:

*   For unit tests of database operation functions, add them to `test_database_util.py`, `test_database_util_ngroup.py` or create a new `test_database_util_<module_name>.py` file.
*   For integration tests of wrapper functions, add them to `test_utils.py`, `test_utils_ngroup.py` or create a new `test_utils_<module_name>.py` file.