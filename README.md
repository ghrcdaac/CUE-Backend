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