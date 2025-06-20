variable "region"{
    type = string
}

variable "access_key" {
    type = string
}

variable "secret_key" {
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