output "sqs_queue_arn" {
  description = "The ARN of the main SQS queue for scan results."
  value       = aws_sqs_queue.scan_results_queue.arn
}

output "scan_event_lambda_arn" {
  description = "The ARN of the cue_scan_event Lambda function."
  value       = aws_lambda_function.cue_scan_event.arn
}

output "event_bus_arn" {
  description = "The ARN of the main application EventBridge bus."
  value       = aws_cloudwatch_event_bus.cue_app_bus.arn
}

output "email_sender_lambda_arn" {
  description = "The ARN of the email_sender Lambda function."
  value       = aws_lambda_function.email_sender.arn
}

output "notification_manager_lambda_arn"{
  description = "The ARN of the notification_manager Lambda function"
  value = aws_lambda_function.notification_manager.arn
}

