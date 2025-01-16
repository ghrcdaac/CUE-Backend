variable "region" {
    type = string
}

variable "account_id" {
    type = string
}

variable "cue_scan_event_role_arn" {
    type = string
}

variable "cue_api_lambda_role_arn"{
    type = string
}

variable "cue_css_scan_sns_arn" {
    type = string
}

variable "db_user" {
    type = string
}

variable "db_host" {
    type = string
}

variable "db_database" {
    type = string
}

variable "db_password" {
    type = string
}

variable "db_port" {
    type = string
}

variable "subnet_ids" {
    type = list(string)
}

variable "security_group_ids" {
    type = list(string)
}

variable "api_id" {
    type = string
}

variable "api_docker" {
    type = string
}