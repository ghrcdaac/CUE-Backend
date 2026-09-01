# ==============================================================================
# File: terraform/lambda/variables.tf (V2 Refactored)
# Purpose: Defines input variables for the Lambda module.
# ==============================================================================

variable "region" {
  description = "AWS region."
  type        = string
}

variable "account_id" {
  description = "AWS Account ID."
  type        = string
}

variable "cue_css_scan_sns_arn" {
  description = "ARN of the SNS topic for CUE CSS scans."
  type        = string
}

# --- Database & Networking ---
variable "db_proxy_host" {
  description = "The endpoint of the RDS Proxy."
  type        = string
}

variable "db_port" {
  description = "Database port."
  type        = string
}

variable "db_database" {
  description = "Database name."
  type        = string
}

variable "db_user" {
  description = "Database username."
  type        = string
}

variable "db_password" {
  description = "Database password."
  type        = string
  sensitive   = true
}

variable "subnet_ids" {
  description = "List of subnet IDs for Lambda VPC configuration."
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for Lambda VPC configuration."
  type        = list(string)
}

# --- API Configuration ---
variable "api_id" {
  description = "API Gateway ID."
  type        = string
}

variable "api_docker_uri" {
  description = "ECR Image URI for the API Lambda."
  type        = string
}

variable "s3_upload_bucket" {
  description = "S3 bucket for file uploads."
  type        = string
}

variable "state_bucket" {
  description = "S3 bucket for terraform state and lambda deployments."
  type        = string
}

variable "file_report_bucket" {
  description = "S3 bucket for generated file PDF reports."
  type        = string
}

variable "frontend_url" {
  description = "The root URL of the CUE dashboard frontend, used for email links."
  type        = string
}

variable "frontend_callback_url" {
  description = "The full callback URL for the frontend application after OIDC login."
  type        = string
}

# --- Keycloak Configuration ---
variable "keycloak_issuer" {
  description = "The OIDC issuer URL for the Keycloak realm."
  type        = string
}

variable "keycloak_audience" {
  description = "The expected audience value in the JWT."
  type        = string
}

variable "keycloak_admin_client_id" {
  description = "The client ID for the Keycloak admin client used by the backend."
  type        = string
}

variable "keycloak_admin_client_secret" {
  description = "The client secret for the Keycloak admin client."
  type        = string
  sensitive   = true
}

# --- SES Configuration ---
variable "sender_email" {
  description = "The email address to send notifications from."
  type        = string
}

variable "ses_source_arn" {
  description = "The ARN of the SES identity that is authorized to send emails."
  type        = string
}

variable "ses_configuration_set_name" {
  description = "The name of the SES Configuration Set to use."
  type        = string
}

variable "ses_region" {
  description = "The AWS region where SES is configured."
  type        = string
}

# --- IAM Role ARNs ---
variable "api_lambda_role_arn" {
  description = "IAM Role ARN for the CUE API Lambda."
  type        = string
}

variable "infected_logger_role_arn" {
  description = "IAM Role ARN for the Infected Logger Lambda."
  type        = string
}

variable "notification_manager_role_arn" {
  description = "IAM Role ARN for the Notification Manager Lambda."
  type        = string
}

variable "email_sender_role_arn" {
  description = "IAM Role ARN for the Email Sender Lambda."
  type        = string
}

variable "process_athena_query_role_arn" {
  description = "IAM Role ARN for the Process Athena Query Lambda."
  type        = string
}

variable "file_transfer_role_arn" {
  description = "IAM Role ARN for the File Transfer Lambda."
  type        = string
}

variable "hdf_vulnerability_scanner_role_arn" {
  description = "IAM Role ARN for the HDF Vulnerability Scanner Lambda."
  type        = string
}

variable "notification_manager_scheduler_role_arn"{
  description = "IAM Role ARN for infected notification scheduler role"
  type        = string
}

variable "cost_update_role_arn" {
  description = "IAM Role ARN for the Cost Update Lambda"
  type        = string
}

variable "css_cost_explorer_role_arn" {
  description = "IAM Role ARN for the external css cost explorer role "
  type        = string
}


# --- Archive Bucket ---
variable "cue_archive_results_bucket" {
  description = "The S3 bucket for final Athena query results."
  type        = string
}

# --- File Transfer ---
variable cue_staging_bucket {
  description = "The S3 bucket for clean scanned files" 
  type        = string
}

variable "cue_quarantine_bucket" {
  description = "The S3 bucket where infected files are quarantined."
  type        = string
}



# delete later

variable "pool_id" {
  description = "Cognito User Pool ID or similar identifier."
  type        = string
}

variable "client_id" {
  description = "Cognito Client ID or similar identifier."
  type        = string
}

variable "client_secret" {
  description = "Cognito Client Secret or similar identifier."
  type        = string
  sensitive   = true // Mark client_secret as sensitive
}

variable "lambda_env_vars" {
  description = "A map of additional environment variables for the Lambda functions."
  type        = map(string)
  default     = {}
}

variable "app_env" {
  type        = string
  description = "The name of the deployment environment (e.g., sit, uat, prod)."
}

variable "keycloak_certs_file" {
  description = "The Keycloak public key location."
  type        = string
}

variable "notification_schedule_minutes" {
  description = "How often (in minutes) the infected file notification schedule runs and how far back the Lambda looks."
  type        = number
  default     = 30 
}

# --- Scalability & Environment Tuning Variables (SIT/UAT vs PROD) ---
variable "api_provisioned_concurrency" { type = number }
variable "scan_event_provisioned_concurrency" { type = number }
variable "file_transfer_provisioned_concurrency" { type = number }
variable "hdf_scanner_provisioned_concurrency" { type = number }
variable "api_pool_max_size" { type = number }
variable "api_pool_min_size" { type = number }

# --- Lambda Memory Configuration Variables ---
variable "api_lambda_memory_size" { type = number }
variable "scan_event_lambda_memory_size" { type = number }
variable "notification_manager_lambda_memory_size" { type = number }
variable "file_transfer_lambda_memory_size" { type = number }
variable "hdf_scanner_lambda_memory_size" { type = number }