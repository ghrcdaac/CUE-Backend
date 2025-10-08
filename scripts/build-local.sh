#!/bin/bash

# ==============================================================================
# File: build-local.sh 
# Purpose: Orchestrates the full build and deployment process for a local environment.
# ==============================================================================

set -e # Exit immediately if a command exits with a non-zero status.

# --- Validate Environment and Set AWS Profile ---
if [ -z "${APP_ENV}" ]; then
    echo "ERROR: APP_ENV is not set. Please source your environment file first (e.g., 'source env-sit.sh')."
    exit 1
fi

case "${APP_ENV}" in
    (sit)
        # Replace with your actual SIT profile name 
        AWS_PROFILE_NAME="cue-sit"
        ;;
    (uat)
        # Replace with your actual UAT profile name
        AWS_PROFILE_NAME="cue-uat"
        ;;
    (prod)
        # Replace with your actual PROD profile name
        AWS_PROFILE_NAME="cue-prod"
        ;;
    (*)
        echo "ERROR: Invalid APP_ENV '${APP_ENV}'. Must be one of 'sit', 'uat', or 'prod'."
        exit 1
        ;;
esac

export AWS_PROFILE="${AWS_PROFILE_NAME}"
echo "Environment detected: ${APP_ENV}"
echo "Using AWS Profile:   ${AWS_PROFILE}"
# --- END NEW SECTION ---

# --- Validate Core Variables ---
if [ -z "${bamboo_ACCOUNT_ID}" ] || [ -z "${bamboo_AWS_REGION}" ]; then
    echo "ERROR: bamboo_ACCOUNT_ID and bamboo_AWS_REGION must be set in your env file."
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

# The AWS_PROFILE exported above will be automatically used by the AWS CLI in this script
API_DOCKER_URI=$(bash ./scripts/build-api.sh "${bamboo_ACCOUNT_ID}" "${bamboo_AWS_REGION}" "${API_IMAGE_TAG}" | grep "@sha256:" | tail -n 1)

echo "${API_DOCKER_URI}"

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
export TF_VAR_app_env="${APP_ENV}"
export TF_VAR_region="${bamboo_AWS_REGION}"
export TF_VAR_account_id="${bamboo_ACCOUNT_ID}"
export TF_VAR_db_password="${bamboo_DB_PASSWORD}"
export TF_VAR_security_group_ids="${bamboo_SECURITY_GROUP_IDS}"
export TF_VAR_subnet_ids="${bamboo_SUBNET_IDS}"
export TF_VAR_lambda_execution_policy_arn="${bamboo_LAMBDA_EXECUTION_POLICY_ARN}"
export TF_VAR_cue_css_scan_sns_arn="${bamboo_CUE_CSS_SCAN_SNS_ARN}"
export TF_VAR_rds_cluster_identifier="${bamboo_RDS_CLUSTER_IDENTIFIER}"
export TF_VAR_api_id="${bamboo_API_ID}"
export TF_VAR_cue_staging_bucket="${bamboo_S3_STAGING_BUCKET}"
export TF_VAR_s3_upload_bucket="${bamboo_S3_UPLOAD_BUCKET}"
export TF_VAR_cue_archive_bucket="${bamboo_S3_ARCHIVE_BUCKET}"
export TF_VAR_cue_archive_results_bucket="${bamboo_S3_ARCHIVE_RESULTS_BUCKET}"
export TF_VAR_pool_id="${bamboo_POOL_ID}"
export TF_VAR_client_id="${bamboo_CLIENT_ID}"
export TF_VAR_client_secret="${bamboo_CLIENT_SECRET}"
export TF_VAR_keycloak_issuer="${bamboo_KEYCLOAK_ISSUER}"
export TF_VAR_keycloak_audience="${bamboo_KEYCLOAK_AUDIENCE}"
export TF_VAR_keycloak_admin_client_id="${bamboo_KEYCLOAK_ADMIN_CLIENT_ID}"
export TF_VAR_keycloak_admin_client_secret="${bamboo_KEYCLOAK_ADMIN_CLIENT_SECRET}"
export TF_VAR_frontend_url="${bamboo_FRONTEND_URL}"
export TF_VAR_frontend_callback_url="${bamboo_FRONTEND_CALLBACK_URL}"
export TF_VAR_keycloak_certs_file="${bamboo_KEYCLOAK_CERTS_FILE}"
export TF_VAR_sender_email="${bamboo_SENDER_EMAIL}"
export TF_VAR_ses_source_arn="${bamboo_SES_SOURCE_ARN}"
export TF_VAR_ses_configuration_set_name="${bamboo_SES_CONFIGURATION_SET_NAME}"
export TF_VAR_ses_region="${bamboo_SES_REGION}"
export TF_VAR_metric_retention_period_name="${bamboo_METRIC_RETENTION_PERIOD_NAME}"
export TF_VAR_metric_retention_period_value="${bamboo_METRIC_RETENTION_PERIOD_VALUE}"
export TF_VAR_glue_availability_zone="${bamboo_GLUE_AVAILABILITY_ZONE}"
export TF_VAR_glue_subnet_id="${bamboo_GLUE_SUBNET_ID}"
export TF_VAR_cue_archive_database_name="${bamboo_CUE_ARCHIVE_DATABASE_NAME}"


# Terraform will automatically use the AWS_PROFILE exported at the top
echo "Initializing Terraform..."
terraform init \
    -reconfigure \
    -upgrade \
    -backend-config="bucket=${bamboo_STATE_BUCKET}" \
    -backend-config="key=terraform.tfstate" \
    -backend-config="region=${bamboo_AWS_REGION}"

# echo "STEP 3A: Creating Terraform plan..."
# terraform plan -out=tfplan

# echo "------------------------------------------------------------------------"
# echo "Terraform plan created at 'terraform/tfplan'."
# echo "Please review the plan. It will show you exactly what will be added, changed, or destroyed."
# echo "Pay close attention to any resources marked for replacement (shown as '-/+')."
# echo "------------------------------------------------------------------------"

# read -p "Do you want to apply this plan? (y/n) " -n 1 -r
# echo
# if [[ $REPLY =~ ^[Yy]$ ]]; then
#     echo "STEP 3B: Applying Terraform configuration..."
#     terraform apply "tfplan"
#     echo "Deployment complete."
# else
#     echo "Plan not applied. Exiting."
#     exit 0
# fi


terraform apply -auto-approve

