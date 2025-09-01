variable "rds_cluster_identifier" {
  type = string
}

variable "db_password" {
  description = "The password for the master user."
  type        = string
  sensitive   = true
}

variable "security_group_ids" {
  description = "List of security group IDs to associate with the RDS Proxy."
  type        = list(string)
}

variable "subnet_ids" {
  description = "List of subnet IDs for the RDS Proxy."
  type        = list(string)
}

variable "db_proxy_iam_role_arn" {
  description = "The ARN of the IAM role that the RDS Proxy will assume."
  type        = string
}