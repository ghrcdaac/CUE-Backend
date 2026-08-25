
variable "region" {
  description = "AWS region."
  type        = string
}

variable "account_id" {
  description = "AWS Account ID."
  type        = string
}


variable "db_user" {
  description = "Database username."
  type        = string
}

variable "db_proxy_host" {
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

variable "metric_retention_period_name" {
  description = "Name of the ssm parameter for the metric retention period"
  type        = string
}

variable "cue_archive_bucket" {
  description = "Bucket containing archived partition parquet files"
  type        = string   
}

variable "subnet_id" {
  description = "Subnet ID for Glue VPC connection."
  type        = string
}

variable "security_group_ids" {
  description = "List of security group IDs for Glue VPC connection."
  type        = list(string)
}

variable "availability_zone" {
  description = "Availability zone for Glue VPC configuration."
  type        = string
}

variable "rds_cluster_identifier" {
  description = "The identifier of the RDS cluster for IAM policy scoping."
  type        = string
}

variable "file_report_bucket" {
  description = "The S3 bucket where file reports are stored."
  type        = string
}

variable "sender_email" {
  description = "The email address sending reports."
  type        = string
}

variable "ses_region" {
  description = "The AWS region for SES."
  type        = string
}

variable "ses_source_arn" {
  description = "The ARN of the SES identity."
  type        = string
  default     = null
}

variable "ses_configuration_set_name" {
  description = "The SES configuration set name."
  type        = string
  default     = null
}