# ./terraform/modules.tf

module "iam_role" {
  source = "./iam"

  # Pass in standard variables
  region                      = var.region
  account_id                  = var.account_id
  lambda_execution_policy_arn = var.lambda_execution_policy_arn
  cue_css_scan_sns_arn        = var.cue_css_scan_sns_arn
  cue_staging_bucket          = var.cue_staging_bucket
  cue_manifest_report_bucket  = var.cue_manifest_report_bucket

  sqs_queue_arn             = module.lambda_functions.sqs_queue_arn
  scan_event_lambda_arn     = module.lambda_functions.scan_event_lambda_arn
  event_bus_arn             = module.lambda_functions.event_bus_arn
  email_sender_lambda_arn   = module.lambda_functions.email_sender_lambda_arn
}

module "lambda_functions" {
  source = "./lambda"

  # --- Pass in required variables ---
  region                      = var.region
  account_id                  = var.account_id
  lambda_execution_policy_arn = var.lambda_execution_policy_arn
  cue_css_scan_sns_arn        = var.cue_css_scan_sns_arn

  # --- Role ARNs from the iam module ---
  cue_scan_event_role_arn     = module.iam_role.cue_scan_event_role_arn
  cue_api_lambda_role_arn     = module.iam_role.cue_api_lambda_role_arn
  notification_manager_role_arn = module.iam_role.notification_manager_role_arn
  email_sender_role_arn       = module.iam_role.email_sender_role_arn

  # --- Database variables ---
  db_host                     = module.rds.db_host
  db_port                     = module.rds.db_port
  db_database                 = module.rds.db_database
  db_user                     = module.rds.db_user
  db_password                 = var.db_password

  # --- Networking variables ---
  subnet_ids                  = var.subnet_ids
  security_group_ids          = var.security_group_ids

  # --- API variables ---
  api_id                      = var.api_id
  api_docker                  = var.api_docker
  pool_id                     = var.pool_id
  client_id                   = var.client_id
  client_secret               = var.client_secret
  s3_upload_bucket            = var.s3_upload_bucket
    
  # --- SES variables ---
  sender_email                = var.sender_email
  ses_source_arn              = var.ses_source_arn
  ses_configuration_set_name  = var.ses_configuration_set_name
  ses_region                  = var.ses_region
}

module "rds" {
  source = "./rds"
  rds_cluster_identifier = var.rds_cluster_identifier
}


module "glue"{
    source = "./glue"

    region = var.region
    account_id = var.account_id
    db_host = module.rds.db_host
    db_port = module.rds.db_port
    db_database = module.rds.db_database
    db_user = module.rds.db_user
    db_password = var.db_password
    cue_glue_job_role_arn = module.iam_role.cue_glue_job_role_arn
    cue_archive_bucket = var.cue_archive_bucket
    metric_retention_period_name = var.metric_retention_period_name
    subnet_id = var.glue_subnet_id
    security_group_ids = var.security_group_ids
    availability_zone = var.glue_availability_zone

}

module "archive_api"{
    source = "./archive-api"

    region = var.region
    account_id = var.account_id
    cue_archive_api_lambda_role_arn = module.iam_role.cue_archive_api_lambda_role_arn
    cue_archive_database_name = var.cue_archive_database_name
    subnet_ids = var.subnet_ids
    security_group_ids = var.security_group_ids
    cue_archive_bucket = var.cue_archive_bucket
    cue_archive_results_bucket = var.cue_archive_results_bucket
    cue_crawler_role_arn = module.iam_role.cue_crawler_role_arn

}

module "s3_replication"{
  source = "./s3_replication"
  region = var.region
  account_id = var.account_id
  cue_staging_bucket = var.cue_staging_bucket
  cue_manifest_report_bucket = var.cue_manifest_report_bucket
  cue_replication_dest_test_bucket = var.cue_replication_dest_test_bucket
  cue_replication_role_arn = module.iam_role.cue_staging_bucket_replication_role_arn
}
