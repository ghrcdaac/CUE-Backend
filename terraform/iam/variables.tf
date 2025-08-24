# ./terraform/iam/variables.tf

variable "region" {
    type = string
}

variable "account_id" {
    type = string
}

variable "cue_css_scan_sns_arn" {
    type = string
}

variable "lambda_execution_policy_arn" {
    type = string
}

# --- NEW: Variables for resources created in the lambda module ---
variable "event_bus_arn" {
  description = "The ARN of the EventBridge bus."
  type        = string
}

variable "email_sender_lambda_arn" {
  description = "The ARN of the email_sender Lambda function."
  type        = string
}

variable "sqs_queue_arn" {
  description = "The ARN of the main SQS queue for scan results."
  type        = string
}

variable "scan_event_lambda_arn" {
  description = "The ARN of the cue_scan_event Lambda function."
  type        = string
}

variable "notification_manager_lambda_arn" {
  description = "The ARN of the notification_manger Lambda function"
  type        = string
}

variable "cue_staging_bucket" {
  description = "The CUE Staging bucket"
  type        = string
}

variable "file_transfer_lambda_arn" {
  description = "The ARN of the file transfer Lambda function"
  type        = string
}
variable "cue_clean_sqs_queue_arn" {
  description = "The ARN of the clean file sqs queue arn"
  type        = string
}