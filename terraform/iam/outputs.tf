output "cue_scan_event_role_arn" {
    value = aws_iam_role.cue_scan_event_role.arn
}

output "cue_api_lambda_role_arn" {
    value = aws_iam_role.cue_api_lambda_role.arn
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