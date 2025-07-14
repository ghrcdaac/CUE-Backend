#!/bin/bash

# This script orchestrates the full build and deployment process for a local environment.
# It sources environment variables, builds artifacts, and runs terraform apply.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Load Environment Variables ---
# An env.sh file is present in the root directory.
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
echo "Using AWS Region:     ${bamboo_AWS_REGION}"
echo "---"

# --- Build Lambda Artifacts ---
echo "STEP 1: Building Lambda artifacts..."
bash ./scripts/build.sh

#--- Build and Push API Docker Image ---
echo "STEP 2: Building and pushing API Docker image..."
# The image tag can be parameterized, using 'latest' for local builds is common.
API_IMAGE_TAG="latest"
bash ./scripts/build-api.sh "${bamboo_ACCOUNT_ID}" "${bamboo_AWS_REGION}" "${API_IMAGE_TAG}"

# --- Deploy with Terraform ---
echo "STEP 3: Running Terraform deployment..."
cd terraform


# The docker image URI needs to be constructed for Terraform
export TF_VAR_api_docker="${bamboo_ACCOUNT_ID}.dkr.ecr.${bamboo_AWS_REGION}.amazonaws.com/cue/api:${API_IMAGE_TAG}"

terraform init \
  -reconfigure \
  -backend-config="bucket=$STATE_BUCKET" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=$AWS_DEFAULT_REGION"


# Export all other variables for Terraform
export TF_VAR_region="${bamboo_AWS_REGION}"
export TF_VAR_account_id="${bamboo_ACCOUNT_ID}"
export TF_VAR_access_key="${bamboo_AWS_ACCESS_KEY_ID}"
export TF_VAR_secret_key="${bamboo_AWS_SECRET_ACCESS_KEY}"
export TF_VAR_db_password="${bamboo_DB_PASSWORD}"
export TF_VAR_security_group_ids="${bamboo_SECURITY_GROUP_IDS}"
export TF_VAR_subnet_ids="${bamboo_SUBNET_IDS}"
export TF_VAR_cue_css_scan_sns_arn="${bamboo_CUE_CSS_SCAN_SNS_ARN}"
export TF_VAR_rds_cluster_identifier="${bamboo_RDS_CLUSTER_IDENTIFIER}"
export TF_VAR_lambda_execution_policy_arn="${bamboo_LAMBDA_EXECUTION_POLICY_ARN}"
export TF_VAR_api_id="${bamboo_API_ID}"
export TF_VAR_pool_id="${bamboo_POOL_ID}"
export TF_VAR_client_id="${bamboo_CLIENT_ID}"
export TF_VAR_client_secret="${bamboo_CLIENT_SECRET}"
export TF_VAR_lambda_env_vars="${bamboo_LAMBDA_ADDITIONAL_ENV_VARS}"
export TF_VAR_s3_upload_bucket="${bamboo_S3_UPLOAD_BUCKET}"

# --- Export SES variables for Terraform ---
export TF_VAR_sender_email="${bamboo_SENDER_EMAIL}"
export TF_VAR_ses_source_arn="${bamboo_SES_SOURCE_ARN}"
export TF_VAR_ses_configuration_set_name="${bamboo_SES_CONFIGURATION_SET_NAME}"
export TF_VAR_ses_region="${bamboo_SES_REGION}"

export TF_VAR_lambda_env_vars="${bamboo_LAMBDA_ADDITIONAL_ENV_VARS:-'{ "POOL_MIN_SIZE": "1", "POOL_MAX_SIZE": "70" }'}"
export TF_VAR_cue_archive_bucket="${bamboo_S3_ARCHIVE_BUCKET}"
export TF_VAR_metric_retention_period_name="${bamboo_METRIC_RETENTION_PERIOD_NAME}"
export TF_VAR_metric_retention_period_value="${bamboo_METRIC_RETENTION_PERIOD_VALUE}"
export TF_VAR_glue_availability_zone="${bamboo_GLUE_AVAILABILITY_ZONE}"
export TF_VAR_glue_subnet_id="${bamboo_GLUE_SUBNET_ID}"
export TF_VAR_cue_archive_database_name="${bamboo_CUE_ARCHIVE_DATABASE_NAME}"
export TF_VAR_cue_archive_results_bucket="${bamboo_S3_ARCHIVE_RESULTS_BUCKET}"
export TF_VAR_cost_explorer_role="${bamboo_COST_EXPLORER_ROLE}"

echo "Initializing Terraform..."
terraform init \
  -reconfigure \
  -backend-config="bucket=${bamboo_STATE_BUCKET}" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=${bamboo_AWS_REGION}"

echo "Applying Terraform configuration..."
terraform apply -auto-approve

echo "Deployment complete."

# --- Use this for a Safer Deployment Workflow to create plan ---
# echo "STEP 3A: Creating Terraform plan..."
# # This saves the plan to a file so we can review it before applying.
# terraform plan -out=tfplan

# echo "------------------------------------------------------------------------"
# echo "Terraform plan created at 'terraform/tfplan'."
# echo "Please review the plan. It will show you exactly what will be added, changed, or destroyed."
# echo "Pay close attention to any resources marked for replacement (shown as '-/+')."
# echo "------------------------------------------------------------------------"

# # Ask for confirmation before applying the plan.
# read -p "Do you want to apply this plan? (yes/no) " -n 1 -r
# echo # Move to a new line
# if [[ $REPLY =~ ^[Yy]$ ]]
# then
#     echo "STEP 3B: Applying Terraform configuration..."
#     terraform apply "tfplan"
#     echo "Deployment complete."
# else
#     echo "Plan not applied. Exiting."
#     exit 0
# fi