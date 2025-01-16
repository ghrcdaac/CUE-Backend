output "cue_scan_event_role_arn" {
    value = aws_iam_role.cue_scan_event_role.arn
}

output "cue_api_lambda_role_arn" {
    value = aws_iam_role.cue_api_lambda_role.arn
}
