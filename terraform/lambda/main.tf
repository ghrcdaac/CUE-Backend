
resource "aws_lambda_function" "cue_scan_event" {
    filename                = "../artifacts/infected-logger-lambda.zip"
    function_name           = "cue_scan_event"
    role                    = var.cue_scan_event_role_arn
    handler                 = "infected-logger.handler"
    runtime                 = "python3.12"
    source_code_hash        = filesha256("../artifacts/infected-logger-lambda.zip")
    timeout                 = 180
    environment {
        variables = {
            DB_USER = var.db_user
            DB_HOST = var.db_host
            DB_DATABASE = var.db_database
            DB_PASSWORD = var.db_password
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
