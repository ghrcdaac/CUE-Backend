# ==============================================================================
# File: terraform/iam/outputs.tf (V2 Corrected & Complete)
# Purpose: Defines all outputs from the IAM module.
# ==============================================================================

output "cue_api_lambda_role_arn" {
  description = "ARN for the CUE API Lambda Role"
  value       = aws_iam_role.cue_api_lambda_role.arn
}

output "infected_logger_role_arn" {
  description = "ARN for the Infected Logger (SQS Consumer) Lambda Role"
  value       = aws_iam_role.infected_logger_role.arn
}

output "notification_manager_role_arn" {
  description = "ARN for the Notification Manager Lambda Role"
  value       = aws_iam_role.notification_manager_role.arn
}

output "email_sender_role_arn" {
  description = "ARN for the Email Sender Lambda Role"
  value       = aws_iam_role.email_sender_role.arn
}

output "process_athena_query_role_arn" {
  description = "ARN for the Process Athena Query Lambda Role"
  value       = aws_iam_role.process_athena_query_role.arn
}

output "file_transfer_role_arn" {
  description = "ARN for the File Transfer Lambda Role"
  value       = aws_iam_role.file_transfer_role.arn
}

output "db_proxy_iam_role_arn" {
  description = "ARN for the RDS Proxy IAM Role"
  value       = aws_iam_role.db_proxy_iam_role.arn
}

output "eventbridge_lambda_scheduler_role_arn" {
  description = "ARN for the notification_scheduler_role_arn"
  value       =  aws_iam_role.eventbridge_lambda_scheduler_role.arn
}

output "cost_update_role_arn" {
  description = "ARN for the Cost Update Lambda Role"
  value = data.aws_iam_role.cue_cost_explorer_role.arn
}

output "manual_file_transfer_role_arn" {
  description = "ARN for the Manual File Transfer Lambda Role"
  value = aws_iam_role.manual_file_transfer_role.arn
}

output "manual_email_sender_role_arn" {
  description = "ARN for the Manual Email Sender Lambda Role"
  value = aws_iam_role.manual_email_sender_role.arn
}

output "manual_notification_manager_role_arn" {
  description = "ARN for the Manual File Transfer Lambda Role"
  value = aws_iam_role.manual_notification_manager_role.arn
}

output "manual_process_athena_query_role_arn" {
  description = "ARN for the Manual File Transfer Lambda Role"
  value = aws_iam_role.manual_process_athena_query_role.arn
}

output "manual_cost_update_role_arn" {
  description = "ARN for the Manual File Transfer Lambda Role"
  value = aws_iam_role.manual_cost_update_role.arn
}

output "manual_infected_logger_role_arn" {
  description = "ARN for the Manual File Transfer Lambda Role"
  value = aws_iam_role.manual_infected_logger_role.arn
}

output "cleanup_uploads_role_arn"{
  description = "ARN for the Cleanup Uploads Lambda Role"
  value = aws_iam_role.cleanup_uploads_role.arn
}