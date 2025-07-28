output "cue_scan_event_role_arn" {
  description = "ARN for the CUE Scan Event Lambda Role"
  value       = aws_iam_role.cue_scan_event_role.arn
}

output "cue_api_lambda_role_arn" {
  description = "ARN for the CUE API Lambda Role"
  value       = aws_iam_role.cue_api_lambda_role.arn
}

output "notification_manager_role_arn" {
  description = "ARN for the Notification Manager Lambda Role"
  value       = aws_iam_role.notification_manager_role.arn
}

output "email_sender_role_arn" {
  description = "ARN for the Email Sender Lambda Role"
  value       = aws_iam_role.email_sender_role.arn
}

output "cue_glue_job_role_arn" {
  value = aws_iam_role.cue_glue_job_role.arn

}

output "cue_archive_api_lambda_role_arn"{
  value = aws_iam_role.cue_archive_api_lambda_role.arn
}

output "cue_crawler_role_arn"{
  value = aws_iam_role.cue_crawler_role.arn

}

output "cue_staging_bucket_replication_role_arn"{
  value = aws_iam_role.cue_staging_bucket_replication_role.arn
}