#!/bin/bash

# ==============================================================================
# File: env.sh.template (V2 Update)
# Purpose: Provides a template for all environment variables needed for deployment.
# ==============================================================================

# --- AWS Credentials & Region ---
export bamboo_AWS_ACCESS_KEY_ID="YOUR_BAMBOO_AWS_ACCESS_KEY_ID_VALUE"
export bamboo_AWS_SECRET_ACCESS_KEY="YOUR_BAMBOO_AWS_SECRET_KEY_VALUE"
export bamboo_AWS_REGION="us-west-2"
export bamboo_ACCOUNT_ID="123456789012"

# --- Terraform State ---
export bamboo_STATE_BUCKET="your-terraform-state-bucket-name"

# --- Database ---
export bamboo_DB_PASSWORD="YOUR_RDS_DATABASE_PASSWORD_VALUE"
export bamboo_RDS_CLUSTER_IDENTIFIER="your-rds-cluster-identifier-from-aws"

# --- Networking ---
export bamboo_SECURITY_GROUP_IDS='["sg-yourFirstSecurityGroupId","sg-yourSecondSecurityGroupId"]'
export bamboo_SUBNET_IDS='["subnet-yourFirstSubnetId","subnet-yourSecondSubnetId"]'
export bamboo_GLUE_SUBNET_ID="yourGlueSubnetId"
export bamboo_GLUE_AVAILABILITY_ZONE="yourGlueAvailabilityZone"

# --- Service ARNs & IDs ---
export bamboo_CUE_CSS_SCAN_SNS_ARN="arn:aws:sns:us-west-2:123456789012:your-cue-css-scan-topic"
export bamboo_LAMBDA_EXECUTION_POLICY_ARN="arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
export bamboo_API_ID="yourApiGatewayRestApiId"
export bamboo_API_DOCKER_URI="123456789012.dkr.ecr.us-west-2.amazonaws.com/your-api-image:latest"

# --- S3 Buckets ---
export bamboo_S3_UPLOAD_BUCKET="your-file-upload-bucket-name"
export bamboo_S3_ARCHIVE_BUCKET="your-archive-bucket-name" 
export bamboo_S3_ARCHIVE_RESULTS_BUCKET="your-archive-results-bucket" 
export bamboo_S3_STAGING_BUCKET="your-cue-staging-bucket"

# --- V1 Cognito Variables (Preserved for backward compatibility) ---
export bamboo_POOL_ID="yourCognitoUserPoolId"
export bamboo_CLIENT_ID="yourCognitoAppClientId"
export bamboo_CLIENT_SECRET="YOUR_COGNITO_APP_CLIENT_SECRET_VALUE"

# --- V2 KEYCLOAK & FRONTEND VARIABLES (NEW) ---
export bamboo_KEYCLOAK_ISSUER="https://idfs.uat.earthdatacloud.nasa.gov/realms/cue"
export bamboo_KEYCLOAK_AUDIENCE="cue-uat"
export bamboo_KEYCLOAK_ADMIN_CLIENT_ID="your-keycloak-admin-client-id"
export bamboo_KEYCLOAK_ADMIN_CLIENT_SECRET="YOUR_KEYCLOAK_ADMIN_CLIENT_SECRET"
export bamboo_FRONTEND_URL="http://localhost:3000"
export bamboo_FRONTEND_CALLBACK_URL="http://localhost:3000/callback"

# --- SES (Email) Configuration ---
export bamboo_SENDER_EMAIL="cue-no-reply@nasa.gov"
export bamboo_SES_REGION="us-east-1"
export bamboo_SES_SOURCE_ARN="arn:aws:ses:us-east-1:123456789012:identity/yourdomain.com"
export bamboo_SES_CONFIGURATION_SET_NAME="CUE-App-Configuration-Set"

# --- Glue & Athena Configuration ---
export bamboo_METRIC_RETENTION_PERIOD_NAME="/cue/config/metric-retention-period"
export bamboo_METRIC_RETENTION_PERIOD_VALUE="90"
export bamboo_CUE_ARCHIVE_DATABASE_NAME="cue_archive_db"
export bamboo_NOTIFICATION_SCHEDULE_MINUTES=30
export bamboo_CLEANUP_UPLOADS_SCHEDULE="cron(0 1 * * ? * )"


