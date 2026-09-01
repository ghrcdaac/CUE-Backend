# ==============================================================================
# File: terraform/lambda/main.tf
# Purpose: Defines all Lambda functions and their event-driven infrastructure,
#          combining all V2 requirements and best practices.
# ==============================================================================

# --- SNS Subscription ---
# Subscribes the SQS queue to the external virus scanner's SNS topic.

 resource "aws_sns_topic_subscription" "cue_scan_event_sns_subscription" {
   topic_arn            = var.cue_css_scan_sns_arn
   protocol             = "sqs"
   endpoint             = aws_sqs_queue.scan_results_queue.arn
   raw_message_delivery = "true"
 }

# --- Lambda Function Definitions ---

# 1. Main API Lambda (Docker Image)
resource "aws_lambda_function" "cue_api" {
  function_name = "cue_api"
  role          = var.api_lambda_role_arn
  image_uri     = var.api_docker_uri
  package_type  = "Image"
  timeout       = 28 # Fail safely before API Gateway 29s timeout
  memory_size      = var.api_lambda_memory_size
  publish = true # This enables versioning, which is required for an alias

  
  tracing_config {
    mode = "Active"
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  environment {
    variables = {
      PG_HOST                        = var.db_proxy_host
      PG_PORT                        = var.db_port
      PG_DB                          = var.db_database
      PG_USER                        = var.db_user
      PG_PASS                        = var.db_password
      S3_UPLOAD_BUCKET               = var.s3_upload_bucket
      EVENT_BUS_NAME                 = aws_cloudwatch_event_bus.cue_app_bus.name
      KEYCLOAK_ISSUER                = var.keycloak_issuer
      KEYCLOAK_AUDIENCE              = var.keycloak_audience
      KEYCLOAK_ADMIN_CLIENT_ID       = var.keycloak_admin_client_id
      KEYCLOAK_ADMIN_CLIENT_SECRET   = var.keycloak_admin_client_secret
      FRONTEND_URL                   = var.frontend_url
      FRONTEND_CALLBACK_URL          = var.frontend_callback_url
      KEYCLOAK_CERTS_FILE            = var.keycloak_certs_file
      LOG_LEVEL                      = "INFO"
      POOL_ID          = var.pool_id
      CLIENT_ID        = var.client_id
      CLIENT_SECRET    = var.client_secret
      POOL_MIN_SIZE    = var.api_pool_min_size
      POOL_MAX_SIZE    = var.api_pool_max_size
      ATHENA_DB_NAME="cue-uat-athena"
      ATHENA_OUTPUT_BUCKET="cue-uat-athena"
      ATHENA_RESULTS_BUCKET="cue-uat-athena"
      DB_SSL_MODE="require"
      API_ROOT_PATH = "/api"
      DEBUG = "True"
      ENV = "production"
      REDEPLOY_TRIGGER = "23"
      FILE_REPORT_BUCKET                   = var.file_report_bucket
      SENDER_EMAIL                         = var.sender_email
      SES_REGION                           = var.ses_region
      SES_SOURCE_ARN                       = var.ses_source_arn
      SES_CONFIGURATION_SET_NAME           = var.ses_configuration_set_name
    }
  }

  lifecycle {
    create_before_destroy = true
  }

}

# 2. Scan Event Logger Lambda (SQS Consumer)
resource "aws_lambda_function" "cue_scan_event" {
  filename         = "../artifacts/infected-logger-lambda.zip"
  source_code_hash = filebase64sha256("../artifacts/infected-logger-lambda.zip")
  function_name    = "cue_scan_event" 
  role             = var.infected_logger_role_arn
  handler          = "handler.handler"
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  timeout          = 180
  memory_size      = var.scan_event_lambda_memory_size
  publish          = true

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  environment {
    variables = {
      PG_HOST        = var.db_proxy_host
      PG_PORT        = var.db_port
      PG_DB          = var.db_database
      PG_USER        = var.db_user
      PG_PASS        = var.db_password
      LOG_LEVEL      = "INFO"
      EVENT_BUS_NAME = aws_cloudwatch_event_bus.cue_app_bus.name
      QUEUE_URL      = aws_sqs_queue.cue_file_transfer_queue.url
      DB_SSL_MODE    = "require"
      ENV = "production"
      REDEPLOY_TRIGGER = "13"
      FILE_TRANSFER_LAMBDA_NAME = aws_lambda_alias.cue_file_transfer_live_alias.arn
      TRANSFER_INVOCATION_MODE  = "LAMBDA"  # This can take 2 values: LAMBDA or SQS
      INFECTED_FILE_THRESHOLD = "5"
      BLOCKING_LOOKBACK_HOURS = "1"
      ENABLE_HDF5_SCANNER = "true"
      HDF_VULNERABILITY_SCANNER_LAMBDA_NAME = aws_lambda_alias.hdf_vulnerability_scanner_live_alias.arn
    }
  }
}

# 3. Notification Manager Lambda
resource "aws_lambda_function" "notification_manager" {
  filename         = "../artifacts/notification-manager-lambda.zip"
  source_code_hash = filebase64sha256("../artifacts/notification-manager-lambda.zip")
  function_name    = "cue_notification_manager"
  role             = var.notification_manager_role_arn
  handler          = "handler.handler"
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  timeout          = 120
  memory_size      = var.notification_manager_lambda_memory_size

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  environment {
    variables = {
      PG_HOST          = var.db_proxy_host
      PG_PORT          = var.db_port
      PG_DB            = var.db_database
      PG_USER          = var.db_user
      PG_PASS          = var.db_password
      EMAIL_SENDER_ARN = aws_lambda_function.email_sender.arn
      FRONTEND_URL     = var.frontend_url
      LOG_LEVEL        = "INFO"
      DB_SSL_MODE    = "require"
      ENV = "production"
      REDEPLOY_TRIGGER = "10"
      NOTIFICATION_SCHEDULE_MINUTES = tostring(var.notification_schedule_minutes)
      INFECTED_FILE_THRESHOLD       = "6"
      BLOCKING_LOOKBACK_HOURS = "1"
    }
  }
}

# 4. Email Sender Lambda
# resource "aws_lambda_function" "email_sender" {
#   filename         = "../artifacts/email-sender-lambda.zip"
#   source_code_hash = filebase64sha256("../artifacts/email-sender-lambda.zip")
#   function_name    = "cue_email_sender"
#   role             = var.email_sender_role_arn
#   handler          = "handler.handler"
#   runtime          = "python3.13"
#   architectures    = ["x86_64"]
#   timeout          = 30
#   memory_size      = 128

#   environment {
#     variables = {
#       SENDER_EMAIL           = var.sender_email
#       SOURCE_ARN             = var.ses_source_arn
#       CONFIGURATION_SET_NAME = var.ses_configuration_set_name
#       SES_REGION             = var.ses_region
#       LOG_LEVEL              = "INFO"
#     }
#   }
# }

# 5. Process Athena Query Lambda
#  resource "aws_lambda_function" "process_athena_query" {
#   filename         = "../artifacts/process-athena-query-lambda.zip"
#   source_code_hash = filebase64sha256("../artifacts/process-athena-query-lambda.zip")
#   function_name    = "cue_process_athena_query"
#   role             = var.process_athena_query_role_arn
#   handler          = "handler.handler"
#   runtime          = "python3.13"
#   architectures    = ["x86_64"]
#   timeout          = 180

#   environment {
#     variables = {
#       RESULTS_BUCKET = var.cue_archive_results_bucket
#       LOG_LEVEL      = "INFO"
#     }
#   }
# }

# 6. File Transfer Lambda
resource  "aws_lambda_function" "cue_file_transfer"{
  filename         = "../artifacts/file-transfer-lambda.zip"
  function_name    = "cue_file_transfer"
  role             = var.file_transfer_role_arn
  handler          = "handler.handler"
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  source_code_hash = filesha256("../artifacts/file-transfer-lambda.zip")
  timeout          = 180
  # Increase Memory for More CPU Power ---
  # Increased from the default of 128MB to 1024MB. This provides more
  # CPU, which is critical for I/O-heavy tasks like file transfers.
  memory_size      = var.file_transfer_lambda_memory_size
  publish          = true

  environment {
    variables = {
      PG_USER        = var.db_user
      PG_HOST        = var.db_proxy_host
      PG_DB          = var.db_database
      PG_PASS        = var.db_password
      PG_PORT        = var.db_port
      STAGING_BUCKET = var.cue_staging_bucket
      LOG_LEVEL      = "INFO"
      DB_SSL_MODE    = "require"
      ENV = "production"
      VERIFY_CHECKSUM_ON_TRANSFER = "true"
      REDEPLOY_TRIGGER = "17"
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }
}

resource "aws_s3_object" "hdf_vulnerability_scanner_zip" {
  bucket = var.state_bucket
  key    = "deployments/hdf-vulnerability-scanner-lambda.zip"
  source = "../artifacts/hdf-vulnerability-scanner-lambda.zip"
  etag   = filemd5("../artifacts/hdf-vulnerability-scanner-lambda.zip")
}

# 7. HDF Vulnerability Scanner Lambda
resource "aws_lambda_function" "hdf_vulnerability_scanner" {
  function_name    = "cue_hdf_vulnerability_scanner"
  role             = var.hdf_vulnerability_scanner_role_arn
  handler          = "handler.handler"
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  
  s3_bucket        = aws_s3_object.hdf_vulnerability_scanner_zip.bucket
  s3_key           = aws_s3_object.hdf_vulnerability_scanner_zip.key
  source_code_hash = filebase64sha256("../artifacts/hdf-vulnerability-scanner-lambda.zip")
  timeout          = 180
  memory_size      = var.hdf_scanner_lambda_memory_size
  publish          = true

  environment {
    variables = {
      PG_USER                   = var.db_user
      PG_HOST                   = var.db_proxy_host
      PG_DB                     = var.db_database
      PG_PASS                   = var.db_password
      PG_PORT                   = var.db_port
      STAGING_BUCKET            = var.cue_staging_bucket
      QUARANTINE_BUCKET         = var.cue_quarantine_bucket
      FILE_TRANSFER_LAMBDA_NAME = aws_lambda_alias.cue_file_transfer_live_alias.arn
      LOG_LEVEL                 = "INFO"
      DB_SSL_MODE               = "require"
      ENV                       = "production"
      REDEPLOY_TRIGGER = "4"
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }
}

# #7. Cost Update Lambda
# resource "aws_lambda_function" "cue_cost_update" {
#   filename         = "../artifacts/cost-update-lambda.zip"
#   source_code_hash = filesha256("../artifacts/cost-update-lambda.zip")
#   function_name    = "cue_cost_update"
#   role             = var.cost_update_role_arn 
#   handler          = "handler.handler"
#   runtime          = "python3.13"
#   architectures    = ["x86_64"]
#   timeout          = 180

#   environment {
#     variables = {
#       PG_USER       = var.db_user
#       PG_HOST       = var.db_proxy_host
#       PG_DB         = var.db_database
#       PG_PASS       = var.db_password
#       PORT          = var.db_port
#       POOL_MIN_SIZE = "1"
#       POOL_MAX_SIZE = "20"
#       LOG_LEVEL     = "INFO"
#       CSS_ROLE_ARN  = var.css_cost_explorer_role_arn
#       DB_SSL_MODE   = "require"
#       ENV           = "production"
#     }
#   }

#   vpc_config {
#     subnet_ids         = var.subnet_ids
#     security_group_ids = var.security_group_ids
#   }
# }


resource "aws_lambda_alias" "cue_api_live_alias" {
  name             = var.app_env
  description      = "The ${var.app_env} alias for production traffic"
  function_name    = aws_lambda_function.cue_api.function_name
  function_version = aws_lambda_function.cue_api.version

  lifecycle {
    create_before_destroy = true
  }
}

# 3. Attaches 1 provisioned (warm) instance to the "live" alias AND waits for it to be ready
resource "aws_lambda_provisioned_concurrency_config" "cue_api_pc" {
  count                             = var.api_provisioned_concurrency > 0 ? 1 : 0
  function_name                     = aws_lambda_function.cue_api.function_name
  provisioned_concurrent_executions = var.api_provisioned_concurrency
  qualifier                         = aws_lambda_alias.cue_api_live_alias.name

  # This explicit dependency ensures the alias is created/updated before this resource is applied.
  depends_on = [aws_lambda_alias.cue_api_live_alias]

  # This provisioner is the key to solving the race condition. It forces Terraform
  # to pause the 'apply' process until AWS confirms the warm instance is fully ready.
  provisioner "local-exec" {
    # --- Using a single-line command to avoid shell interpretation issues ---
    command = "aws lambda wait function-updated --function-name ${self.function_name} --qualifier ${self.qualifier}"
  }
}


resource "aws_lambda_alias" "cue_scan_event_live_alias" {
  name             = var.app_env
  description      = "The ${var.app_env} alias for the scan event function"
  function_name    = aws_lambda_function.cue_scan_event.function_name
  function_version = aws_lambda_function.cue_scan_event.version

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_provisioned_concurrency_config" "scan_event_pc" {
  count                             = var.scan_event_provisioned_concurrency > 0 ? 1 : 0
  function_name                     = aws_lambda_function.cue_scan_event.function_name
  provisioned_concurrent_executions = var.scan_event_provisioned_concurrency
  qualifier                         = aws_lambda_alias.cue_scan_event_live_alias.name
  depends_on                        = [aws_lambda_alias.cue_scan_event_live_alias]

  provisioner "local-exec" {
    command = "aws lambda wait function-updated --function-name ${self.function_name} --qualifier ${self.qualifier}"
  }
}


resource "aws_lambda_permission" "cue_api_apigw_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"

  function_name = aws_lambda_alias.cue_api_live_alias.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.region}:${var.account_id}:${var.api_id}/*/*/*"
  depends_on = [aws_lambda_provisioned_concurrency_config.cue_api_pc]
}


# Add Provisioned Concurrency for the File Transfer Lambda ---
# This keeps one instance of the Lambda "warm" at all times, eliminating
# cold start delays and ensuring the fastest possible response time.

resource "aws_lambda_alias" "cue_file_transfer_live_alias" {
  name             = var.app_env
  description      = "The ${var.app_env} alias for the file transfer function"
  function_name    = aws_lambda_function.cue_file_transfer.function_name
  function_version = aws_lambda_function.cue_file_transfer.version

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_provisioned_concurrency_config" "file_transfer_pc" {
  count                             = var.file_transfer_provisioned_concurrency > 0 ? 1 : 0
  function_name                     = aws_lambda_function.cue_file_transfer.function_name
  provisioned_concurrent_executions = var.file_transfer_provisioned_concurrency
  qualifier                         = aws_lambda_alias.cue_file_transfer_live_alias.name
   depends_on = [aws_lambda_alias.cue_file_transfer_live_alias]

  provisioner "local-exec" {
    command = "aws lambda wait function-updated --function-name ${self.function_name} --qualifier ${self.qualifier}"
  }
}

resource "aws_lambda_alias" "hdf_vulnerability_scanner_live_alias" {
  name             = var.app_env
  description      = "The ${var.app_env} alias for the hdf vulnerability scanner function"
  function_name    = aws_lambda_function.hdf_vulnerability_scanner.function_name
  function_version = aws_lambda_function.hdf_vulnerability_scanner.version

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_provisioned_concurrency_config" "hdf_vulnerability_scanner_pc" {
  count                             = var.hdf_scanner_provisioned_concurrency > 0 ? 1 : 0
  function_name                     = aws_lambda_function.hdf_vulnerability_scanner.function_name
  provisioned_concurrent_executions = var.hdf_scanner_provisioned_concurrency
  qualifier                         = aws_lambda_alias.hdf_vulnerability_scanner_live_alias.name
  depends_on                        = [aws_lambda_alias.hdf_vulnerability_scanner_live_alias]

  provisioner "local-exec" {
    command = "aws lambda wait function-updated --function-name ${self.function_name} --qualifier ${self.qualifier}"
  }
}

# --- Event Triggers and Permissions ---

resource "aws_lambda_event_source_mapping" "scan_event_trigger" {
  event_source_arn = aws_sqs_queue.scan_results_queue.arn
  function_name    = aws_lambda_alias.cue_scan_event_live_alias.arn
  batch_size       = 5
}

resource "aws_lambda_event_source_mapping" "file_transfer_queue_to_transfer_lambda" {
  event_source_arn = aws_sqs_queue.cue_file_transfer_queue.arn
  function_name    = aws_lambda_alias.cue_file_transfer_live_alias.arn
  batch_size       = 10
  maximum_batching_window_in_seconds = 0 
  function_response_types  = ["ReportBatchItemFailures"]
  scaling_config {
    maximum_concurrency = 50
  }
}

# --- Lambda Permissions ---

resource "aws_lambda_permission" "allow_eventbridge_to_notification_manager" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notification_manager.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.application_events_rule.arn
}
# resource "aws_lambda_permission" "allow_eventbridge_to_update_cost" {
#   statement_id  = "AllowExecutionFromEventBridge"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.cue_cost_update.function_name
#   principal     = "events.amazonaws.com"
#   source_arn    = aws_cloudwatch_event_rule.cost_update_schedule.arn
# }


# resource "aws_lambda_permission" "allow_eventbridge_to_athena_processor" {
#   statement_id  = "AllowExecutionFromEventBridgeForAthena"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.process_athena_query.function_name
#   principal     = "events.amazonaws.com"
#   source_arn    = aws_cloudwatch_event_rule.athena_query_state_change_rule.arn
# }

# resource "aws_lambda_permission" "cue_api_apigw_permission" {
#   statement_id  = "AllowExecutionFromAPIGateway"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.cue_api.function_name
#   principal     = "apigateway.amazonaws.com"
#   source_arn    = "arn:aws:execute-api:${var.region}:${var.account_id}:${var.api_id}/*/*/*"
# }

# --- CloudWatch Log Groups ---

resource "aws_cloudwatch_log_group" "api_lambda_lg" {
  name              = "/aws/lambda/${aws_lambda_function.cue_api.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "scan_event_lg" {
  name              = "/aws/lambda/${aws_lambda_function.cue_scan_event.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "notification_manager_lg" {
  name              = "/aws/lambda/${aws_lambda_function.notification_manager.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "email_sender_lg" {
  name              = "/aws/lambda/${aws_lambda_function.email_sender.function_name}"
  retention_in_days = 14
}

# resource "aws_cloudwatch_log_group" "process_athena_query_lg" {
#   name              = "/aws/lambda/${aws_lambda_function.process_athena_query.function_name}"
#   retention_in_days = 14
# }

