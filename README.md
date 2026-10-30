# CUE - Cloud Upload Environment Backend

## 1. Overview

This repository contains the backend source code and infrastructure definitions for the CUE (Cloud Upload Environment) application.

CUE provides a cloud-native solution for NASA DAACs (Distributed Active Archive Centers) to replace on-premises file upload capabilities for non-ICD (Interface Control Document) compliant providers. It aims to prevent compromised files from entering the DAAC environment by scanning them for malicious content.

The backend consists of:

- A **FastAPI** application providing RESTful APIs for the CUE dashboard.
- Integration with **AWS Cognito** for user authentication (SRP).
- A **PostgreSQL** database for storing application data.
- **Event-driven Lambda functions** for background processing (e.g., logging).
- Infrastructure managed via **Terraform**.
- Containerization using **Docker** for local development and deployment.

## 2. Prerequisites

Before you begin, ensure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- [Poetry](https://python-poetry.org/docs/#installation)
- [AWS CLI](https://aws.amazon.com/cli/)
- [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) (optional)

## 3. Local Development Setup (Docker Compose)

### 3.1. Clone the Repository

```bash
git clone https://github.com/ghrcdaac/CUE-Backend.git
cd CUE-Backend
```

### 3.2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit the `.env` file with your preferred local settings. Key variables to set include:

- `PG_USER`, `PG_PASS`, `PG_DB`: Credentials for PostgreSQL.
- `POOL_ID`, `CLIENT_ID`, `CLIENT_SECRET`:  Cognito values 
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`: 
- `PGADMIN_DEFAULT_EMAIL`, `PGADMIN_DEFAULT_PASSWORD`: Credentials for pgAdmin.
- Ensure `ENV=dev` and `DEBUG=true`.

(Note: Test database variables `PG_DB_TEST`, `PG_USER_TEST`, etc., are only needed for local integration tests.)

### 3.3. Build and Run Containers

```bash
docker compose up --build -d
```

- `--build` ensures updated images.
- `-d` runs containers in detached mode.

The PostgreSQL container will auto-run SQL scripts from `src/postgres/` to initialize the schema.

### 3.4. Accessing Services

- **API**: [http://localhost:8000](http://localhost:8000)
- **Swagger UI**: [http://localhost:8000/v1/docs](http://localhost:8000/v1/docs)
- **pgAdmin**: [http://localhost:8001](http://localhost:8001)

pgAdmin connection details:

- Host: `postgres`
- Port: `5432`
- Database: value of `PG_DB`
- Username: value of `PG_USER`
- Password: value of `PG_PASS`

### 3.5. Stopping the Environment

```bash
docker compose down        # Stops containers
docker compose down -v     # Also removes volumes and data
```

## 4. Build & Deployment (Simulating CI/CD)

### 4.1. Packaging Lambda Functions

```bash
bash scripts/build.sh
```

This script:

- Creates a temporary directory.
- Installs dependencies from `src/python/event_lambdas/requirements.txt`.
- Copies shared utilities from `src/python/lambda_utils`.
- Creates `my_deployment_package.zip`.
- Packages each Lambda (e.g., `infected-logger`) into `artifacts/<lambda_name>-lambda.zip`.

### 4.2. Building and Pushing the API Docker Image

```bash
aws ecr get-login-password --region <your-aws-region> | docker login --username AWS --password-stdin <your-ecr-url>

# For ARM64 (Lambda)
docker buildx build --platform linux/arm64 -t <your-ecr-repo-name>:<your-tag> -f Dockerfile.aws .

# For AMD64
# docker build -t <your-ecr-repo-name>:<your-tag> -f Dockerfile.aws .

docker tag <your-ecr-repo-name>:<your-tag> <your-ecr-url>/<your-ecr-repo-name>:<your-tag>

docker push <your-ecr-url>/<your-ecr-repo-name>:<your-tag>
```

### 4.3. Deploying Infrastructure with Terraform

Used in CI/CD pipelines (e.g., Bamboo). Do not run locally unless deploying.

Process:

- Calls `bash ./scripts/build.sh` to prep packages.
- Sets environment variables (`TF_VAR_*`, AWS keys, state bucket, etc.).
- Enters `terraform/` and runs:

```bash
terraform init
terraform apply -auto-approve
```

This applies updates to Lambdas, API Gateway, RDS, IAM, etc.

## 5. Important Note on Infrastructure Management

The following AWS resources are typically managed manually to prevent accidental changes:

- VPC, Subnets, Security Groups
- RDS instances/clusters
- S3 buckets (esp. for Terraform state)
- Cognito User Pools
- Core API Gateway

Terraform scripts refer to these using existing IDs/ARNs passed as variables (`TF_VAR_*`).

## 6. Metrics age-off into S3 
In order to preserve the database performance file metric data are aged-off into a S3 bucket using an scheduled AWS Glue Job. The glue job finds file metric data in the database that is outside of a configurable retention period, writes the data to partitioned parquet files, uploads the files to a s3 bucket, then removes the archived data from the database. 

Configuration for the glue job is done with the following:
- The retention period is fetched from a SSM parameter.  
- The execution schedule is configured by a glue job trigger.

The glue job script is in `src/python/glue_jobs/` and infrastructure is contained within the module `terraform/glue`.

Glue job runs are logged into Cloudwatch.

## 7. CUE desktop app (GUI) support

### 7.1. Environment variables
| Variable | Default | Purpose |
| --- | --- | --- |
| `DESKTOP_REDIRECT_URIS` | empty | Comma-separated exact allow-list of desktop sign-in redirect URIs (for example `http://127.0.0.1:53117/callback,http://127.0.0.1:53118/callback,http://127.0.0.1:53119/callback`). Empty disables the desktop sign-in endpoints (404). |
| `UPLOAD_PROVIDER_CHECK_MODE` | `legacy` | `legacy` = today's upload check; `strict` = the uploader must be assigned to a provider mapped to the collection. |

Both are wired like `KEYCLOAK_ISSUER`: `bamboo_*` in the env files → `TF_VAR_*` in `scripts/build-local.sh` → `terraform/variables.tf` → `terraform/modules.tf` → `terraform/lambda`.

### 7.2. Database updates
Run the `[GUI-1]` … `[GUI-7]` statements at the end of `src/postgres/9-updates.sql` one at a time (SIT → UAT → PROD), then the `[GUI-check]` query (expected = actual). Run the read-only `[GUI-orphans]` query first: it lists collections whose `provider_id` points to a provider that no longer exists, which the backfill and the view skip. They only add new objects (`collection_provider`, `mapping_history`, the `v_collection_provider` view, two indexes) and backfill one row per collection; existing tables are untouched. Every statement is idempotent. Fresh databases get the same objects from `2-tables.sql`.

### 7.3. Endpoints
- `GET /v2/me/upload-targets?include_unavailable=false&search=` — collections the caller can upload to, with their providers, plus non-secret `caller` info (name; for API keys also key name, last 4 characters, expiry, scopes, type). Accepts a Keycloak JWT **or** a `cue_sk_` API key with `file:upload`.
  - admin: all collections; `daac_manager` / `daac_staff` / `security` and proxy keys: all collections in their DAACs; everyone else: collections mapped to providers they're assigned to, within their DAACs.

- Desktop sign-in (existing Keycloak client + PKCE S256 + loopback redirect). All three return 404 while `DESKTOP_REDIRECT_URIS` is empty; the Dashboard login endpoints are unchanged.
  - `POST /v2/auth/desktop/login-url` `{redirect_uri, code_challenge, code_challenge_method: "S256", state}` → `{login_url}` (`redirect_uri` must be exactly in the allow-list).
  - `POST /v2/auth/desktop/token` `{code, redirect_uri, code_verifier}` → tokens (same shape as `/v2/auth/exchange-code`). Keycloak rejections → 400 with a generic message; Keycloak/network failures → 502.
  - `POST /v2/auth/desktop/logout` `{refresh_token}` → 204 always. Revokes the refresh token at Keycloak's `/revoke` endpoint (not `/logout`, so the browser/Dashboard session stays signed in).
  - Refresh uses the existing `POST /v2/auth/refresh`.

API keys are accepted only by `/v2/upload/*`, `POST /v2/files/list` (`apiKey` in the body), and `GET /v2/me/upload-targets`. `src/python/api/tests/test_api_key_allowlist.py` fails if any other endpoint starts accepting keys.

### 7.4. Tests
```bash
pytest -o addopts="" src/python/api/tests
```
These tests need no database (the DB layer is mocked). The older tests in `tests/` need a test database and currently fail to import (`tests/conftest.py` uses a relative import); that's a pre-existing issue.
