variable "region"{
    type = string
}

variable "account_id" {
    type = string
}

variable "db_password" {
    type = string
}

variable "security_group_ids" {
    type = list(string)
}

variable "subnet_ids" {
    type = list(string)
}

variable "cue_css_scan_sns_arn" {
    type = string
}

variable "rds_cluster_identifier" {
    type = string
}

variable "lambda_execution_policy_arn" {
    type = string
}

variable "api_id" {
    type = string
}

variable "api_docker" {
    type = string
}

variable "pool_id" {
    type = string
}

variable "client_id"{
    type = string
}

variable "client_secret"{
    type = string
}


variable "s3_upload_bucket"{
    type = string
}


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
}

variable "cue_archive_bucket" {
    type = string
}

variable "metric_retention_period_value" {
    type = string
}

variable "metric_retention_period_name" {
    type = string
}

variable "glue_availability_zone" {

    type = string
}

variable "glue_subnet_id" {
    type = string
}

variable "cue_archive_database_name" {
    type = string
}

variable "cue_archive_results_bucket" {
    type = string
} 

