#!/bin/bash
bash ./scripts/build.sh

export AWS_ACCESS_KEY_ID="${bamboo_AWS_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${bamboo_AWS_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION="${bamboo_AWS_REGION}"
export STATE_BUCKET="${bamboo_STATE_BUCKET}"

# --- TEMPORARY DEBUGGING  ---
echo "SCRIPT USING AWS_ACCESS_KEY_ID: [${AWS_ACCESS_KEY_ID}]"
echo "SCRIPT USING AWS_DEFAULT_REGION: [${AWS_DEFAULT_REGION}]"
echo "SCRIPT USING STATE_BUCKET: [${STATE_BUCKET}]"
echo "AWS_SECRET_ACCESS_KEY length: ${#AWS_SECRET_ACCESS_KEY}"
# --- END TEMPORARY DEBUGGING ---

# Test credentials with AWS CLI 
aws sts get-caller-identity
if [ $? -ne 0 ]; then
  echo "AWS CLI get-caller-identity failed. Check credentials."
  exit 1
fi

cd terraform

terraform init \
  -reconfigure \
  -backend-config="bucket=$STATE_BUCKET" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=$AWS_DEFAULT_REGION"

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
export TF_VAR_api_docker="${bamboo_API_DOCKER}"
export TF_VAR_pool_id="${bamboo_POOL_ID}"
export TF_VAR_client_id="${bamboo_CLIENT_ID}"
export TF_VAR_client_secret="${bamboo_CLIENT_SECRET}"
export TF_VAR_lambda_env_vars="${bamboo_LAMBDA_ADDITIONAL_ENV_VARS:-'{ "POOL_MIN_SIZE": "1", "POOL_MAX_SIZE": "70" }'}"
export TF_VAR_s3_upload_bucket="${bamboo_S3_UPLOAD_BUCKET}"

terraform apply -auto-approve
