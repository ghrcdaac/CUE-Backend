# ./terraform/lambda/main.tf

# --- SNS Subscription ---
# This subscribes the SQS queue (defined in sqs.tf) to the SNS topic.
resource "aws_sns_topic_subscription" "cue_scan_even_sns_subscription" {
  topic_arn            = var.cue_css_scan_sns_arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.scan_results_queue.arn
  raw_message_delivery = "true"
}

# --- Lambda Function Definitions ---

resource "aws_lambda_function" "cue_scan_event" {
  filename         = "../artifacts/infected-logger-lambda.zip"
  function_name    = "cue_scan_event"
  role             = var.cue_scan_event_role_arn
  handler          = "infected_logger.handler.handler"
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  source_code_hash = filesha256("../artifacts/infected-logger-lambda.zip")
  timeout          = 180
  memory_size      = 256

  environment {
    variables = {
      PG_USER       = var.db_user
      PG_HOST       = var.db_host
      PG_DB         = var.db_database
      PG_PASS       = var.db_password
      PG_PORT       = var.db_port
      POOL_MIN_SIZE = lookup(var.lambda_env_vars, "POOL_MIN_SIZE", "1")
      POOL_MAX_SIZE = lookup(var.lambda_env_vars, "POOL_MAX_SIZE", "20")
      LOG_LEVEL     = lookup(var.lambda_env_vars, "LOG_LEVEL", "INFO")
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.cue_scan_event_lg.name
  }
}

resource "aws_lambda_function" "notification_manager" {
  filename         = "../artifacts/notification-manager-lambda.zip"
  function_name    = "cue_notification_manager"
  role             = var.notification_manager_role_arn
  handler          = "notification_manager.handler.handler"
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  source_code_hash = filesha256("../artifacts/notification-manager-lambda.zip")
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      PG_USER          = var.db_user
      PG_HOST          = var.db_host
      PG_DB            = var.db_database
      PG_PASS          = var.db_password
      PG_PORT          = var.db_port
      POOL_MIN_SIZE    = "1"
      POOL_MAX_SIZE    = "20"
      LOG_LEVEL        = "INFO"
      EMAIL_SENDER_ARN = aws_lambda_function.email_sender.arn
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }
}

resource "aws_lambda_function" "cue_api" {
  function_name = "cue_api"
  role          = var.cue_api_lambda_role_arn
  image_uri     = var.api_docker
  package_type  = "Image"
  timeout       = 180
  kms_key_arn   = null

  environment {
    variables = {
      PG_USER          = var.db_user
      PG_HOST          = var.db_host
      PG_DB            = var.db_database
      PG_PASS          = var.db_password
      PG_PORT          = var.db_port
      POOL_ID          = var.pool_id
      CLIENT_ID        = var.client_id
      CLIENT_SECRET    = var.client_secret
      POOL_MIN_SIZE    = lookup(var.lambda_env_vars, "POOL_MIN_SIZE", "1")
      POOL_MAX_SIZE    = lookup(var.lambda_env_vars, "POOL_MAX_SIZE", "70")
      S3_UPLOAD_BUCKET = var.s3_upload_bucket
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }
}

# --- Triggers, Events, and other resources ---

# RESTORED: This trigger now correctly points from SQS directly to the cue_scan_event Lambda.
resource "aws_lambda_event_source_mapping" "scan_event_trigger" {
  event_source_arn = aws_sqs_queue.scan_results_queue.arn
  function_name    = aws_lambda_function.cue_scan_event.arn
  batch_size       = 5
}

resource "aws_cloudwatch_event_rule" "infected_file_rule" {
  name           = "cue-infected-file-found-rule"
  description    = "Triggers notification manager for infected files"
  event_bus_name = aws_cloudwatch_event_bus.cue_app_bus.name
  event_pattern = jsonencode({
    source      = ["com.cue.scanner"],
    "detail-type" = ["InfectedFileFound"]
  })
}

resource "aws_cloudwatch_event_target" "infected_file_target" {
  rule           = aws_cloudwatch_event_rule.infected_file_rule.name
  target_id      = "TriggerNotificationManager"
  arn            = aws_lambda_function.notification_manager.arn
  event_bus_name = aws_cloudwatch_event_bus.cue_app_bus.name
}

resource "aws_lambda_permission" "allow_eventbridge_to_notification_manager" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notification_manager.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.infected_file_rule.arn
}

resource "aws_lambda_permission" "cue_api_apigw_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cue_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.region}:${var.account_id}:${var.api_id}/*/*/*"
}

# --- Logging ---
resource "aws_cloudwatch_log_group" "cue_scan_event_lg" {
  name              = "/aws/lambda/cue_scan_event"
  retention_in_days = 14
}
