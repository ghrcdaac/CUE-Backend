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
