// ./lambda/variables.tf

variable "region" {
  description = "AWS region."
  type        = string
}

variable "account_id" {
  description = "AWS Account ID."
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
  type        = string // Or number, but your python code uses os.getenv which returns string
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
