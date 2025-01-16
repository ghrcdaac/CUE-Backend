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