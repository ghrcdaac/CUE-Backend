output "cue_scan_event_arn" {
    value = aws_lambda_function.cue_scan_event.invoke_arn
}
