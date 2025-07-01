
variable "region" {
  description = "AWS region."
  type        = string
}

variable "account_id" {
  description = "AWS Account ID."
  type        = string
}

variable "cue_glue_job_role_arn" {
  description = "IAM Role ARN for the CUE Glue Job."
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

