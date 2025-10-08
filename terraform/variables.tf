# ==============================================================================
# File: terraform/variables.tf (V2 Refactored)
# Purpose: Defines all input variables for the root Terraform module.
# ==============================================================================

# --- AWS Provider Configuration ---
variable "region" {
  description = "The AWS region where resources will be deployed."
  type        = string
}

variable "account_id" {
  description = "The AWS Account ID."
  type        = string
}

# --- Networking Configuration ---
variable "subnet_ids" {
  description = "List of subnet IDs for placing resources like Lambdas and RDS Proxy."
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs to apply to network resources."
  type        = list(string)
}

variable "glue_subnet_id" {
  description = "The specific subnet ID for the Glue job connection."
  type        = string
}

variable "glue_availability_zone" {
  description = "The availability zone for the Glue job connection."
  type        = string
}

# --- Database Configuration ---
variable "rds_cluster_identifier" {
  description = "The identifier for the existing RDS Aurora cluster."
  type        = string
}

variable "db_password" {
  description = "The password for the master database user."
  type        = string
  sensitive   = true
}

# --- IAM & SNS (External ARNs) ---
variable "lambda_execution_policy_arn" {
  description = "The ARN for the basic AWSLambdaVPCAccessExecutionRole policy."
  type        = string
}

variable "cue_css_scan_sns_arn" {
  description = "The ARN of the external SNS topic that provides file scan results."
  type        = string
}

# --- S3 Buckets ---
variable "s3_upload_bucket" {
  description = "The name of the S3 bucket where files are initially uploaded."
  type        = string
}

variable "cue_archive_bucket" {
  description = "The name of the S3 bucket for storing archived Glue data (in Parquet format)."
  type        = string
}

variable "cue_archive_results_bucket" {
  description = "The name of the S3 bucket where Athena query results are stored."
  type        = string
}

variable "cue_staging_bucket" {
  description = "The name of the S3 bucket where clean are placed after scanning"
  type        = string
}

# --- API & ECR ---
variable "api_id" {
  description = "The ID of the pre-existing API Gateway."
  type        = string
}

variable "api_docker_uri" {
  description = "The full URI of the Docker image in ECR for the FastAPI application."
  type        = string
}

# --- Keycloak Configuration (V2) ---
variable "keycloak_issuer" {
  description = "The full URL of the Keycloak issuer (e.g., https://id.example.com/realms/myrealm)."
  type        = string
}

variable "keycloak_audience" {
  description = "The audience value expected in the Keycloak JWTs (e.g., 'cue-api')."
  type        = string
}

variable "keycloak_admin_client_id" {
  description = "The Keycloak client ID for the backend service."
  type        = string
}

variable "keycloak_admin_client_secret" {
  description = "The Keycloak client secret for the backend service."
  type        = string
  sensitive   = true
}

variable "keycloak_certs_file" {
  description = "The Keycloak public key location."
  type        = string
}


# --- SES (Email) Configuration ---
variable "sender_email" {
  description = "The 'From' email address for system notifications."
  type        = string
}

variable "ses_source_arn" {
  description = "The ARN of the SES identity (domain or email) authorized to send emails."
  type        = string
}

variable "ses_configuration_set_name" {
  description = "The name of the SES Configuration Set to use for tracking email sending."
  type        = string
}

variable "ses_region" {
  description = "The AWS region where SES is configured (e.g., 'us-east-1')."
  type        = string
}

# --- Glue & Athena Configuration ---
variable "metric_retention_period_name" {
  description = "The name of the SSM Parameter Store parameter for metric retention."
  type        = string
}

variable "metric_retention_period_value" {
  description = "The value for the metric retention period (e.g., '90 days')."
  type        = string
}

variable "cue_archive_database_name" {
  description = "The name of the Athena database for querying archived metrics."
  type        = string
}

# --- Frontend Configuration ---
variable "frontend_url" {
  description = "The root URL of the CUE dashboard, used for links in notification emails."
  type        = string
}

variable "frontend_callback_url" {
  description = "The full callback URL for the OIDC flow."
  type        = string
}

variable "app_env" {
  type        = string
  description = "The name of the deployment environment (e.g., sit, uat, prod)."
}


# delete later

variable "pool_id" {
    type = string
}

variable "client_id"{
    type = string
}

variable "client_secret"{
    type = string
}