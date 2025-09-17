# ==============================================================================
# File: terraform/refactor.tf
# Purpose: This temporary file guides Terraform through our module refactoring
#          to prevent the destruction of existing resources. After one successful
#          apply, this file can be safely deleted.
# ==============================================================================



# --- Move S3 Bucket from old Archive module to Root ---
moved {
  from = module.archive_api.aws_s3_bucket.cue_archive_results_bucket
  to   = aws_s3_bucket.cue_archive_results_bucket
}

# --- Move Archive resources from old `archive_api` module to new `archive` module ---
moved {
  from = module.archive_api.aws_glue_catalog_database.cue_archive_database
  to   = module.archive.aws_glue_catalog_database.cue_archive_database
}
moved {
  from = module.archive_api.aws_glue_catalog_table.metrics
  to   = module.archive.aws_glue_catalog_table.metrics
}
moved {
  from = module.archive_api.aws_glue_crawler.metrics_crawler
  to   = module.archive.aws_glue_crawler.metrics_crawler
}
moved {
  from = module.archive_api.aws_cloudwatch_event_rule.athena_query_rule
  to   = module.archive.aws_cloudwatch_event_rule.athena_query_rule
}

# --- Move IAM Roles to their new self-contained modules ---
moved {
  from = module.iam_role.aws_iam_role.cue_glue_job_role
  to   = module.glue.aws_iam_role.cue_glue_job_role
}
moved {
  from = module.iam_role.aws_iam_role_policy.cue_glue_job_policy
  to   = module.glue.aws_iam_role_policy.cue_glue_job_policy
}
moved {
  from = module.iam_role.aws_iam_role.cue_crawler_role
  to   = module.archive.aws_iam_role.cue_crawler_role
}
moved {
  from = module.iam_role.aws_iam_role_policy.cue_crawler_policy
  to   = module.archive.aws_iam_role_policy.cue_crawler_policy
}

# --- Map Old IAM Role Names to New V2 Role Names ---
# This tells Terraform that the old roles were renamed, not deleted.
moved {
  from = module.iam_role.aws_iam_role.cue_scan_event_role
  to   = module.iam_role.aws_iam_role.infected_logger_role
}
moved {
  from = module.iam_role.aws_iam_role.cue_archive_api_lambda_role
  to   = module.iam_role.aws_iam_role.process_athena_query_role
}

# --- Map Old Lambda resources moved from archive_api to lambda module ---
moved {
  from = module.archive_api.aws_lambda_function.cue_process_athena_query
  to   = module.lambda_functions.aws_lambda_function.process_athena_query
}
moved {
  from = module.archive_api.aws_lambda_permission.athena_rule_permission
  to   = module.lambda_functions.aws_lambda_permission.allow_eventbridge_to_athena_processor
}

# --- Map Consolidated EventBridge Rules ---
# This tells Terraform that the old, specific rules are now part of the new consolidated rule.
moved {
  from = module.lambda_functions.aws_cloudwatch_event_rule.infected_file_rule
  to   = module.lambda_functions.aws_cloudwatch_event_rule.application_events_rule
}
moved {
  from = module.lambda_functions.aws_cloudwatch_event_target.infected_file_target
  to   = module.lambda_functions.aws_cloudwatch_event_target.notification_manager_target
}

