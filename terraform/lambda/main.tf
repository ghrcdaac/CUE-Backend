
resource "aws_lambda_function" "cue_scan_event" {
    filename                = "../artifacts/infected-logger-lambda.zip"
    function_name           = "cue_scan_event"
    role                    = var.cue_scan_event_role_arn
    handler                 = "infected-logger.handler"
    runtime                 = "python3.12"
    architectures           = ["arm64"]
    source_code_hash        = filesha256("../artifacts/infected-logger-lambda.zip")
    timeout                 = 180
    environment {
        variables = {
            PG_USER     = var.db_user     
            PG_HOST     = var.db_host     
            PG_DB       = var.db_database 
            PG_PASS     = var.db_password 
            PG_PORT     = var.db_port
        }
    }
    vpc_config {
        subnet_ids          = var.subnet_ids
        security_group_ids  = var.security_group_ids
    }
}

resource "aws_lambda_permission" "cue_scan_event" {
    statement_id    = "AllowExecutionFromSNS"
    action          = "lambda:InvokeFunction"
    function_name   = aws_lambda_function.cue_scan_event.function_name
    principal       = "sns.amazonaws.com"
    source_arn      = var.cue_css_scan_sns_arn
}

resource "aws_sns_topic_subscription" "cue_scan_even_sns_subscription"{
    topic_arn       = var.cue_css_scan_sns_arn
    protocol        = "lambda"
    endpoint        = aws_lambda_function.cue_scan_event.arn
}

resource "aws_lambda_function" "cue_api"{
    function_name       = "cue_api"
    role                = var.cue_api_lambda_role_arn
    image_uri           = var.api_docker
    package_type        = "Image"
    timeout             = 180
    environment{
        variables = {
            PG_USER = var.db_user
            PG_HOST = var.db_host
            PG_DB = var.db_database
            PG_PASS = var.db_password
            PG_PORT     = var.db_port
            POOL_ID = var.pool_id
            CLIENT_ID = var.client_id
            CLIENT_SECRET = var.client_secret
            POOL_MIN_SIZE = lookup(var.lambda_env_vars, "POOL_MIN_SIZE", "1")
            POOL_MAX_SIZE = lookup(var.lambda_env_vars, "POOL_MAX_SIZE", "70")
            S3_UPLOAD_BUCKET = var.s3_upload_bucket
        }
    }
    vpc_config {
        subnet_ids          = var.subnet_ids
        security_group_ids  = var.security_group_ids
    }
}
resource "aws_lambda_permission" "cue_api" {
    statement_id    = "AllowExecutionFromAPIGateway"
    action          = "lambda:InvokeFunction"
    function_name   = aws_lambda_function.cue_api.function_name
    principal       = "apigateway.amazonaws.com"
    source_arn      = "arn:aws:execute-api:${var.region}:${var.account_id}:${var.api_id}/*/*/*"
}


