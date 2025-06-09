locals {
  cue_scan_event_assume_role_rendered = templatefile("${path.module}/cue_scan_event_assume_role.json", {
    region     = var.region
    account_id = var.account_id
  })

  cue_scan_event_policy_rendered = templatefile("${path.module}/cue_scan_event_policy.json", {
    region               = var.region
    account_id           = var.account_id
    cue_css_scan_sns_arn = var.cue_css_scan_sns_arn
  })

  cue_api_lambda_assume_role_rendered = templatefile("${path.module}/cue_api_lambda_assume_role.json", {
    region     = var.region
    account_id = var.account_id
  })

  cue_api_lambda_policy_rendered = templatefile("${path.module}/cue_api_lambda_policy.json", {
    region     = var.region
    account_id = var.account_id
  })

  cue_glue_job_assume_role_rendered = templatefile("${path.module}/cue_glue_job_assume_role.json", {
    region     = var.region
    account_id = var.account_id
  })

  cue_glue_job_policy_rendered = templatefile("${path.module}/cue_glue_job_policy.json", {
    region     = var.region
    account_id = var.account_id
  })
}