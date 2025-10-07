# ==============================================================================
# File: terraform/modules.tf (V2 Final & Corrected)
# Purpose: Defines and correctly connects all the Terraform modules.
# ==============================================================================

module "iam_role" {
  source = "./iam"

  # --- Pass in standard variables ---
  region                       = var.region
  account_id                   = var.account_id
  lambda_execution_policy_arn  = var.lambda_execution_policy_arn
  s3_upload_bucket             = var.s3_upload_bucket
  cue_archive_bucket           = var.cue_archive_bucket
  cue_archive_results_bucket   = var.cue_archive_results_bucket
  cue_staging_bucket           = var.cue_staging_bucket
  file_transfer_lambda_arn = module.lambda_functions.cue_file_transfer_lambda_alias_arn
}

module "lambda_functions" {
  source = "./lambda"

  # --- Pass in standard variables ---
  region                         = var.region
  account_id                     = var.account_id
  cue_css_scan_sns_arn           = var.cue_css_scan_sns_arn
  frontend_url                   = var.frontend_url
  frontend_callback_url          = var.frontend_callback_url
  api_docker_uri                 = var.api_docker_uri
  api_id                         = var.api_id
  s3_upload_bucket               = var.s3_upload_bucket
  cue_archive_results_bucket     = var.cue_archive_results_bucket
  cue_staging_bucket             = var.cue_staging_bucket

  # --- Pass in V2 Keycloak variables ---
  keycloak_issuer                = var.keycloak_issuer
  keycloak_audience              = var.keycloak_audience
  keycloak_admin_client_id       = var.keycloak_admin_client_id
  keycloak_admin_client_secret   = var.keycloak_admin_client_secret

  # --- Role ARNs from the iam module ---
  api_lambda_role_arn            = module.iam_role.cue_api_lambda_role_arn
  infected_logger_role_arn       = module.iam_role.infected_logger_role_arn
  notification_manager_role_arn  = module.iam_role.notification_manager_role_arn
  email_sender_role_arn          = module.iam_role.email_sender_role_arn
  process_athena_query_role_arn  = module.iam_role.process_athena_query_role_arn
  file_transfer_role_arn         = module.iam_role.file_transfer_role_arn
  

  # --- Database variables (connecting to the RDS Proxy) ---
  db_proxy_host                  = module.rds.db_proxy_host
  db_port                        = module.rds.db_port
  db_database                    = module.rds.db_database
  db_user                        = module.rds.db_user
  db_password                    = var.db_password

  # --- Networking variables ---
  subnet_ids                     = var.subnet_ids
  security_group_ids             = var.security_group_ids

  # --- SES variables ---
  sender_email                   = var.sender_email
  ses_source_arn                 = var.ses_source_arn
  ses_configuration_set_name     = var.ses_configuration_set_name
  ses_region                     = var.ses_region

  #delete later
  pool_id                     = var.pool_id
  client_id                   = var.client_id
  client_secret               = var.client_secret
}

module "rds" {
  source = "./rds"

  rds_cluster_identifier = var.rds_cluster_identifier
  db_password            = var.db_password
  subnet_ids             = var.subnet_ids
  security_group_ids     = var.security_group_ids
  db_proxy_iam_role_arn  = module.iam_role.db_proxy_iam_role_arn
}


module "glue" {
  source = "./glue"

  # --- Pass in required variables ---
  region                       = var.region
  account_id                   = var.account_id
  db_proxy_host                = module.rds.db_proxy_host 
  db_port                      = module.rds.db_port
  db_database                  = module.rds.db_database
  db_user                      = module.rds.db_user
  db_password                  = var.db_password
  cue_archive_bucket           = var.cue_archive_bucket
  metric_retention_period_name = var.metric_retention_period_name
  subnet_id                    = var.glue_subnet_id
  security_group_ids           = var.security_group_ids
  availability_zone            = var.glue_availability_zone
  rds_cluster_identifier = var.rds_cluster_identifier
}

# module "archive" {
#   source = "./archive" # Renamed from archive-api for consistency

#   region                       = var.region
#   account_id                   = var.account_id
#   cue_archive_database_name       = var.cue_archive_database_name
#   cue_archive_bucket              = var.cue_archive_bucket
#   process_athena_query_lambda_arn = module.lambda_functions.process_athena_query_lambda_arn 
# }

