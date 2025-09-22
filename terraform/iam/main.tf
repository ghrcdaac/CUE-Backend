# ==============================================================================
# File: terraform/iam/main.tf (Corrected)
# Purpose: Defines all the IAM Roles with static names to prevent replacement.
# ==============================================================================

# --- Role for the main FastAPI Lambda ---
resource "aws_iam_role" "cue_api_lambda_role" {
  name               = "CUEApiLambdaRole" # Use static name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
}
resource "aws_iam_role_policy" "cue_api_lambda_policy" {
  name   = "CUEApiLambdaPolicy"
  role   = aws_iam_role.cue_api_lambda_role.id
  policy = data.aws_iam_policy_document.api_lambda_policy.json
}
resource "aws_iam_role_policy_attachment" "cue_api_lambda_vpc" {
  role       = aws_iam_role.cue_api_lambda_role.id
  policy_arn = var.lambda_execution_policy_arn
}

# --- Role for the Infected Logger (SQS Consumer) Lambda ---
resource "aws_iam_role" "infected_logger_role" {
  name               = "CUEInfectedLoggerRole" # Use static name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
}
resource "aws_iam_role_policy" "infected_logger_policy" {
  name   = "CUEInfectedLoggerPolicy"
  role   = aws_iam_role.infected_logger_role.id
  policy = data.aws_iam_policy_document.infected_logger_policy.json
}
resource "aws_iam_role_policy_attachment" "infected_logger_vpc" {
  role       = aws_iam_role.infected_logger_role.id
  policy_arn = var.lambda_execution_policy_arn
}
resource "aws_iam_role_policy_attachment" "infected_logger_sqs" {
  role       = aws_iam_role.infected_logger_role.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

# --- Role for the Notification Manager Lambda ---
resource "aws_iam_role" "notification_manager_role" {
  name               = "CUENotificationManagerRole" # Use static name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
}
resource "aws_iam_role_policy" "notification_manager_policy" {
  name   = "CUENotificationManagerPolicy"
  role   = aws_iam_role.notification_manager_role.id
  policy = data.aws_iam_policy_document.notification_manager_policy.json
}
resource "aws_iam_role_policy_attachment" "notification_manager_vpc" {
  role       = aws_iam_role.notification_manager_role.id
  policy_arn = var.lambda_execution_policy_arn
}

# --- Role for the Email Sender Lambda ---
resource "aws_iam_role" "email_sender_role" {
  name               = "CUEEmailSenderRole" # Use static name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
}
resource "aws_iam_role_policy" "email_sender_policy" {
  name   = "CUEEmailSenderPolicy"
  role   = aws_iam_role.email_sender_role.id
  policy = data.aws_iam_policy_document.email_sender_policy.json
}

# --- Role for the Process Athena Query Lambda ---
resource "aws_iam_role" "process_athena_query_role" {
  name               = "CUEProcessAthenaQueryRole" # Use static name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
}
resource "aws_iam_role_policy" "process_athena_query_policy" {
  name   = "CUEProcessAthenaQueryPolicy"
  role   = aws_iam_role.process_athena_query_role.id
  policy = data.aws_iam_policy_document.process_athena_query_policy.json
}

# --- Role for Update File Cost Lambda ---
 #data "aws_iam_role" "cue_cost_explorer_role" {
  #name = var.cue_cost_explorer_role_name
#}

#resource "aws_iam_role_policy_attachment" "cue_cost_update_lambda_execution_role_attach" {
  #role       = data.aws_iam_role.cue_cost_explorer_role.name
  #policy_arn = var.lambda_execution_policy_arn
#}

# --- Role for the File Transfer Lambda ---
resource "aws_iam_role" "file_transfer_role"{
  name               = "CUEFileTransferRole" # Use static name
  assume_role_policy =  data.aws_iam_policy_document.lambda_assume_role_policy.json
}

resource "aws_iam_role_policy_attachment" "file_transfer_vpc" {
  role       = aws_iam_role.file_transfer_role.id
  policy_arn = var.lambda_execution_policy_arn
}

resource "aws_iam_role_policy" "file_transfer_policy" {
  name   = "CUEFileTransferPolicy" 
  role   = aws_iam_role.file_transfer_role.id
  policy = data.aws_iam_policy_document.file_transfer_policy.json
}

# --- Role for Infected files Eventbridge Scheduler ---
resource "aws_iam_role" "notification_manager_scheduler_role" {
  name               = "CUENotificationManagerSchedulerRole" 
  assume_role_policy = data.aws_iam_policy_document.eventbridge_scheduler_assume_role.json
}

resource "aws_iam_role_policy" "notification_manager_scheduler_policy" {
   name       = "CUENotificationManagerSchedulerPolicy"
   role       = aws_iam_role.notification_manager_scheduler_role.id
   policy     = data.aws_iam_policy_document.notification_manager_scheduler_policy.json
}

# --- Role for the RDS Proxy ---
resource "aws_iam_role" "db_proxy_iam_role" {
  name               = "CUERDSProxyRole" # Use static name
  assume_role_policy = data.aws_iam_policy_document.rds_assume_role_policy.json
}

