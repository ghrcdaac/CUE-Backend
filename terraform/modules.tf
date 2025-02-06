module "iam_role" {
    source = "./iam"

    region = var.region
    account_id = var.account_id
    cue_css_scan_sns_arn = var.cue_css_scan_sns_arn
    lambda_execution_policy_arn = var.lambda_execution_policy_arn
}

module "lambda_functions" {
    source = "./lambda"

    region = var.region
    account_id = var.account_id
    cue_scan_event_role_arn = module.iam_role.cue_scan_event_role_arn
    cue_api_lambda_role_arn = module.iam_role.cue_api_lambda_role_arn
    cue_css_scan_sns_arn = var.cue_css_scan_sns_arn
    db_host = module.rds.db_host
    db_port = module.rds.db_port
    db_database = module.rds.db_database
    db_user = module.rds.db_user
    db_password = var.db_password
    subnet_ids = var.subnet_ids
    security_group_ids = var.security_group_ids
    api_id = var.api_id
    api_docker = var.api_docker
    pool_id = var.pool_id
    client_id = var.client_id
    client_secret = var.client_secret
}

module "rds"{
    source = "./rds"

    rds_cluster_identifier = var.rds_cluster_identifier
}