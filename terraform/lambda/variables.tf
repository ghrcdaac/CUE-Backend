// ./lambda/variables.tf

variable "region" {
  description = "AWS region."
  type        = string
}

variable "account_id" {
  description = "AWS Account ID."
  type        = string
}

variable "lambda_execution_policy_arn" {
  description = "The ARN for the basic Lambda execution policy (for VPC access)."
  type        = string
}

variable "cue_css_scan_sns_arn" {
  description = "ARN of the SNS topic for CUE CSS scans."
  type        = string
}

variable "db_user" {
  description = "Database username."
  type        = string
}

variable "db_host" {
  description = "Database host endpoint."
  type        = string
}

variable "db_database" {
  description = "Database name."
  type        = string
}

variable "db_password" {
  description = "Database password."
  type        = string
  sensitive   = true // Mark password as sensitive
}

variable "db_port" {
  description = "Database port."
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for Lambda VPC configuration."
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for Lambda VPC configuration."
  type        = list(string)
}

variable "api_id" {
  description = "API Gateway ID."
  type        = string
}

variable "api_docker" {
  description = "ECR Image URI for the API Lambda."
  type        = string
}

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

variable "s3_upload_bucket" {
  description = "S3 bucket for upload"
  type        = string
}

# --- SES Configuration Variables ---
variable "sender_email" {
  description = "The email address to send notifications from."
  type        = string
}

variable "ses_source_arn" {
  description = "The ARN of the SES identity (domain/email) that is authorized to send emails."
  type        = string
}

variable "ses_configuration_set_name" {
  description = "The name of the SES Configuration Set to use for sending emails."
  type        = string
}

variable "ses_region" {
  description = "The AWS region where SES is configured (often us-east-1)."
  type        = string
}

variable "cue_scan_event_role_arn" {
  description = "IAM Role ARN for the CUE Scan Event Lambda."
  type        = string
}

variable "cue_api_lambda_role_arn" {
  description = "IAM Role ARN for the CUE API Lambda."
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