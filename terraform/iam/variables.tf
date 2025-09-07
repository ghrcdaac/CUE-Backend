# ==============================================================================
# File: terraform/iam/variables.tf (V2 Corrected)
# Purpose: Defines the input variables for the IAM module.
# ==============================================================================

variable "region" {
  description = "The AWS region where resources are deployed."
  type        = string
}

variable "account_id" {
  description = "The AWS Account ID."
  type        = string
}

variable "lambda_execution_policy_arn" {
  description = "The ARN for the basic AWSLambdaVPCAccessExecutionRole policy."
  type        = string
}

variable "s3_upload_bucket" {
  description = "The name of the S3 bucket for file uploads."
  type        = string
}

variable "cue_archive_bucket" {
  description = "The S3 bucket for the Athena archive source."
  type        = string
}

variable "cue_archive_results_bucket" {
  description = "The S3 bucket for Athena query results."
  type        = string
}

variable "cue_staging_bucket" {
  description = "The S3 bucket for clean scanned files."
  type        = string
}

