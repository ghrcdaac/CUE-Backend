#!/bin/bash

# ==============================================================================
# File: build-local.sh (V2 Update)
# Purpose: Orchestrates the full build and deployment process for a local environment.
# ==============================================================================

set -e # Exit immediately if a command exits with a non-zero status.

# --- Load Environment Variables ---
# if [ -f ./env.sh ]; then
#     echo "Sourcing environment variables from env.sh"
#     source ./env.sh
# else
#     echo "ERROR: env.sh file not found. Please create one from env.sh.template."
#     exit 1
# fi

# --- Validate Core Variables ---
if [ -z "${bamboo_ACCOUNT_ID}" ] || [ -z "${bamboo_AWS_REGION}" ]; then
    echo "ERROR: bamboo_ACCOUNT_ID and bamboo_AWS_REGION must be set in env.sh"
    exit 1
fi

echo "---"
echo "Validated environment variables."
echo "Using AWS Account ID: ${bamboo_ACCOUNT_ID}"
echo "Using AWS Region:   ${bamboo_AWS_REGION}"
echo "---"

# --- Build Lambda Artifacts ---
echo "STEP 1: Building Lambda artifacts..."
# bash ./scripts/build.sh

#--- Build and Push API Docker Image ---
echo "STEP 2: Building and pushing API Docker image..."
API_IMAGE_TAG="latest"

API_DOCKER_URI=$(bash ./scripts/build-api.sh "${bamboo_ACCOUNT_ID}" "${bamboo_AWS_REGION}" "${API_IMAGE_TAG}"  | grep "@sha256:" | tail -n 1)

echo ${API_DOCKER_URI}

# 2. Check if the captured URI is a valid ECR digest URI.
#    Then, export the Terraform variable with the captured value.
if [[ -z "$API_DOCKER_URI" ]] || [[ ! "$API_DOCKER_URI" == *"@sha256:"* ]]; then
  echo "ERROR: Failed to retrieve a valid Docker image digest URI from the build script."
  echo "Falling back to default value: ${bamboo_API_DOCKER}"
  export TF_VAR_api_docker_uri="${bamboo_API_DOCKER}"
else
  echo "Successfully retrieved Docker image URI: ${API_DOCKER_URI}"
  export TF_VAR_api_docker_uri="${API_DOCKER_URI}"
fi


echo "TF_VAR_api_docker_uri is set to: $TF_VAR_api_docker_uri"


# --- Deploy with Terraform ---
echo "STEP 3: Running Terraform deployment..."
cd terraform

# --- Export ALL variables for Terraform ---




# Standard AWS & Networking
export TF_VAR_region="${bamboo_AWS_REGION}"
export TF_VAR_account_id="${bamboo_ACCOUNT_ID}"
export TF_VAR_db_password="${bamboo_DB_PASSWORD}"
export TF_VAR_security_group_ids="${bamboo_SECURITY_GROUP_IDS}"
export TF_VAR_subnet_ids="${bamboo_SUBNET_IDS}"
export TF_VAR_lambda_execution_policy_arn="${bamboo_LAMBDA_EXECUTION_POLICY_ARN}"

# Service ARNs & IDs
export TF_VAR_cue_css_scan_sns_arn="${bamboo_CUE_CSS_SCAN_SNS_ARN}"
export TF_VAR_rds_cluster_identifier="${bamboo_RDS_CLUSTER_IDENTIFIER}"
export TF_VAR_api_id="${bamboo_API_ID}"

# S3 Buckets
export TF_VAR_s3_upload_bucket="${bamboo_S3_UPLOAD_BUCKET}"
export TF_VAR_cue_archive_bucket="${bamboo_S3_ARCHIVE_BUCKET}" 
export TF_VAR_cue_archive_results_bucket="${bamboo_S3_ARCHIVE_RESULTS_BUCKET}"

# V1 Cognito (preserved)
export TF_VAR_pool_id="${bamboo_POOL_ID}"
export TF_VAR_client_id="${bamboo_CLIENT_ID}"
export TF_VAR_client_secret="${bamboo_CLIENT_SECRET}"

# V2 Keycloak (NEW)
export TF_VAR_keycloak_issuer="${bamboo_KEYCLOAK_ISSUER}"
export TF_VAR_keycloak_audience="${bamboo_KEYCLOAK_AUDIENCE}"
export TF_VAR_keycloak_admin_client_id="${bamboo_KEYCLOAK_ADMIN_CLIENT_ID}"
export TF_VAR_keycloak_admin_client_secret="${bamboo_KEYCLOAK_ADMIN_CLIENT_SECRET}"

# Frontend URLs (NEW)
export TF_VAR_frontend_url="${bamboo_FRONTEND_URL}"
export TF_VAR_frontend_callback_url="${bamboo_FRONTEND_CALLBACK_URL}"

# SES (Email)
export TF_VAR_sender_email="${bamboo_SENDER_EMAIL}"
export TF_VAR_ses_source_arn="${bamboo_SES_SOURCE_ARN}"
export TF_VAR_ses_configuration_set_name="${bamboo_SES_CONFIGURATION_SET_NAME}"
export TF_VAR_ses_region="${bamboo_SES_REGION}"

# Glue & Athena
export TF_VAR_metric_retention_period_name="${bamboo_METRIC_RETENTION_PERIOD_NAME}"
export TF_VAR_metric_retention_period_value="${bamboo_METRIC_RETENTION_PERIOD_VALUE}"
export TF_VAR_glue_availability_zone="${bamboo_GLUE_AVAILABILITY_ZONE}"
export TF_VAR_glue_subnet_id="${bamboo_GLUE_SUBNET_ID}"
export TF_VAR_cue_archive_database_name="${bamboo_CUE_ARCHIVE_DATABASE_NAME}"

# --- Safer Deployment Workflow ---


echo "Initializing Terraform..."
terraform init \
  -reconfigure \
  -upgrade \
  -backend-config="bucket=${bamboo_STATE_BUCKET}" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=${bamboo_AWS_REGION}"

terraform apply -auto-approve

# echo "STEP 3A: Creating Terraform plan..."
# # This saves the plan to a file so we can review it before applying.
# terraform plan -out=tfplan

# echo "------------------------------------------------------------------------"
# echo "Terraform plan created at 'terraform/tfplan'."
# echo "Please review the plan. It will show you exactly what will be added, changed, or destroyed."
# echo "Pay close attention to any resources marked for replacement (shown as '-/+')."
# echo "------------------------------------------------------------------------"

# # Ask for confirmation before applying the plan.
# read -p "Do you want to apply this plan? (y/n) " -n 1 -r
# echo # Move to a new line
# if [[ $REPLY =~ ^[Yy]$ ]]
# then
#   echo "STEP 3B: Applying Terraform configuration..."
#   terraform apply "tfplan"
#   echo "Deployment complete."
# else
#     echo "Plan not applied. Exiting."
#     exit 0
# fi






# terraform apply -auto-approve




# terraform state rm 'aws_s3_bucket.cue_archive_bucket'
# terraform state rm 'aws_s3_bucket_public_access_block.cue_archive_bucket_access'

# terraform state rm 'aws_s3_bucket_versioning.cue_archive_bucket_versioning'

# terraform state rm 'aws_s3_bucket_server_side_encryption_configuration.cue_archive_bucket_encryption'

# # Move the S3 bucket itself
# terraform state mv 'module.glue.aws_s3_bucket.cue_archive_bucket' 'aws_s3_bucket.cue_archive_bucket'

# # Move the associated bucket configurations
# terraform state mv 'module.glue.aws_s3_bucket_public_access_block.cue_archive_bucket_access' 'aws_s3_bucket_public_access_block.cue_archive_bucket_access'
# terraform state mv 'module.glue.aws_s3_bucket_versioning.cue_archive_bucket_versioning' 'aws_s3_bucket_versioning.cue_archive_bucket_versioning'
# terraform state mv 'module.glue.aws_s3_bucket_server_side_encryption_configuration.cue_archive_bucket_encryption' 'aws_s3_bucket_server_side_encryption_configuration.cue_archive_bucket_encryption'

# terraform import 'module.lambda_functions.aws_cloudwatch_log_group.api_lambda_lg' '/aws/lambda/cue_api'