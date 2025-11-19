# ==============================================================================
# File: terraform/lambda/outputs.tf (V2 Corrected)
# ==============================================================================

output "sqs_queue_arn" {
  description = "The ARN of the main SQS queue for scan results."
  value       = aws_sqs_queue.scan_results_queue.arn
}

output "event_bus_arn" {
  description = "The ARN of the main application EventBridge bus."
  value       = aws_cloudwatch_event_bus.cue_app_bus.arn
}

output "process_athena_query_lambda_arn" {
  description = "The ARN of the process_athena_query Lambda function."
  value       = aws_lambda_function.process_athena_query.arn
}

output "email_sender_lambda_arn" {
  description = "The ARN of the email_sender Lambda function."
  value       = aws_lambda_function.email_sender.arn
}

output "scan_event_lambda_arn" {
  description = "The ARN of the cue_scan_event Lambda function."
  value       = aws_lambda_function.cue_scan_event.arn
}

output "file_transfer_lambda_arn" {
  description = "The ARN of the file transfer Lambda function"
  value = aws_lambda_function.cue_file_transfer.arn
}

output "cue_file_transfer_sqs_queue_arn" {
  description = "The ARN of the clean file sqs queue"
  value = aws_sqs_queue.cue_file_transfer_queue.arn
}

output "cue_file_transfer_lambda_arn" {
  description = "The ARN of the CUE file transfer Lambda function."
  value       = aws_lambda_function.cue_file_transfer.arn
}

output "cue_file_transfer_lambda_alias_arn" {
  description = "The ARN of the CUE file transfer Lambda function's alias."
  value       = aws_lambda_alias.cue_file_transfer_live_alias.arn
}