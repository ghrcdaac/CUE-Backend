variable "region" {
  description = "AWS region for rendering IAM policies and resources."
  type        = string
}

variable "account_id" {
  description = "AWS Account ID for rendering IAM policies."
  type        = string
}

variable "cue_archive_database_name" {
  description = "Name of the archive data catalog database."
  type        = string
}

variable "cue_archive_bucket" {
  description = "S3 bucket containing archived data."
  type        = string
}

variable "process_athena_query_lambda_arn" {
  description = "The ARN of the Lambda function that processes Athena results."
  type        = string
}

