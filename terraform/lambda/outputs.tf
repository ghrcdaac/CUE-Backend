output "event_bus_arn" {
  description = "The ARN of the main application EventBridge bus."
  value       = aws_cloudwatch_event_bus.cue_app_bus.arn
}

output "email_sender_lambda_arn" {
  description = "The ARN of the email_sender Lambda function."
  value       = aws_lambda_function.email_sender.arn
}
