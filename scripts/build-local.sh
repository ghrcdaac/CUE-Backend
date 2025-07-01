#!/bin/bash
bash ./scripts/build.sh

export AWS_ACCESS_KEY_ID="${bamboo_AWS_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${bamboo_AWS_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION="${bamboo_AWS_REGION}"
export STATE_BUCKET="${bamboo_STATE_BUCKET}"

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
export TF_VAR_cue_archive_bucket="${bamboo_S3_ARCHIVE_BUCKET}"
export TF_VAR_metric_retention_period_name="${bamboo_METRIC_RETENTION_PERIOD_NAME}"
export TF_VAR_metric_retention_period_value="${bamboo_METRIC_RETENTION_PERIOD_VALUE}"
export TF_VAR_glue_availability_zone="${bamboo_GLUE_AVAILABILITY_ZONE}"
export TF_VAR_glue_subnet_id="${bamboo_GLUE_SUBNET_ID}"
export TF_VAR_cue_archive_database_name="${bamboo_CUE_ARCHIVE_DATABASE_NAME}"
export TF_VAR_cue_archive_results_bucket="${bamboo_S3_ARCHIVE_RESULTS_BUCKET}"


terraform apply -auto-approve
