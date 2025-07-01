// ./archive-api/variables.tf

variable "region" {
  description = "AWS region."
  type        = string
}

variable "account_id" {
  description = "AWS Account ID."
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

variable "cue_archive_database_name" {
  description = "Name of the archive data catalog database"
  type        = string
}

variable "cue_archive_api_lambda_role_arn" {
  description = "Archive API lambda role ARN"
  type        = string
}

variable "cue_archive_bucket"{
  description = "CUE archive bucket"  
  type        = string
}

variable "cue_archive_results_bucket"{
  description = "CUE archive results bucket"  
  type        = string
}

variable "cue_crawler_role_arn" {
  description = "Glue Crawler role ARN"
  type        = string
}