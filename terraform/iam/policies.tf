# ==============================================================================
# File: terraform/iam/policies.tf (V2 Corrected)
# Purpose: Defines all IAM policy documents for the application's roles.
# ==============================================================================

# --- Assume Role Policies (Trust Policies) ---

data "aws_iam_policy_document" "lambda_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "rds_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["rds.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "glue_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "eventbridge_scheduler_assume_role" { 
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

# --- Permission Policies for Lambda Roles ---

data "aws_iam_policy_document" "api_lambda_policy" {
  statement {
    effect    = "Allow"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["arn:aws:s3:::${var.s3_upload_bucket}/*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:PutObjectTagging"
    ]
    resources = ["arn:aws:s3:::${var.file_report_bucket}/*"]
  }
  statement {
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
  statement {
    effect    = "Allow"
    actions   = ["events:PutEvents"]
    resources = ["arn:aws:events:${var.region}:${var.account_id}:event-bus/cue-application-bus"]
  }
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.region}:${var.account_id}:function:cue_manual_file_transfer"]
  }
}

data "aws_iam_policy_document" "infected_logger_policy" {
  statement {
    effect    = "Allow"
    actions   = ["events:PutEvents"]
    resources = ["arn:aws:events:${var.region}:${var.account_id}:event-bus/cue-application-bus"]
  }
  statement{
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = ["arn:aws:sqs:${var.region}:${var.account_id}:cue-file-transfer-queue"]
  }
}

data "aws_iam_policy_document" "notification_manager_policy" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.region}:${var.account_id}:function:cue_email_sender"]
  }
}

data "aws_iam_policy_document" "email_sender_policy" {
  statement {
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "process_athena_query_policy" {
  statement {
    effect = "Allow"
    actions = [
      "athena:GetQueryExecution",
      "athena:GetQueryResults"
    ]
    resources = ["*"]
  }
  statement {
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:PutObject"]
    resources = [
      "arn:aws:s3:::${var.cue_archive_bucket}/results/*",
      "arn:aws:s3:::${var.cue_archive_results_bucket}/*"
    ]
  }
}

data "aws_iam_policy_document" "file_transfer_policy" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject","s3:GetObjectTagging","s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.cue_staging_bucket}", "arn:aws:s3:::${var.cue_staging_bucket}/*" ]
  }
  statement {
    effect    = "Allow"
    actions   = ["s3:PutObject","s3:PutObjectTagging","s3:PutObjectAcl"]
    resources = ["*"]
  }
  statement {
    effect    = "Allow"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility"]
    resources = ["arn:aws:sqs:${var.region}:${var.account_id}:cue-file-transfer-queue"]
  }
}

data "aws_iam_policy_document" "cost_update_policy"{
  statement{
    effect    = "Allow"
    actions   = ["sts:AssumeRole"]
    resources = ["${var.css_cost_explorer_role_arn}"]
  }
}

data "aws_iam_policy_document" "manual_file_transfer_policy"{
  statement{
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = ["arn:aws:sqs:${var.region}:${var.account_id}:cue-file-transfer-queue"]
  }
  statement{
    effect    = "Allow" 
    actions   = ["s3:GetObject"]
    resources = ["arn:aws:s3:::${var.cue_staging_bucket}", "arn:aws:s3:::${var.cue_staging_bucket}/*" ]
  }
}

data "aws_iam_policy_document" "manual_email_sender_policy" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.region}:${var.account_id}:function:cue_email_sender"]
  }
}

data "aws_iam_policy_document" "manual_notification_manager_policy" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.region}:${var.account_id}:function:cue_notification_manager"]
  }
}

data "aws_iam_policy_document" "manual_process_athena_query_policy" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.region}:${var.account_id}:function:cue_process_athena_query"]
  }

  statement {
    effect = "Allow"
    actions = [
      "athena:GetQueryExecution"
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "manual_cost_update_policy" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.region}:${var.account_id}:function:cue_cost_update"]
  }
}

data "aws_iam_policy_document" "manual_infected_logger_policy" {
  statement {
    effect    = "Allow"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility"]
    resources = ["arn:aws:sqs:${var.region}:${var.account_id}:cue-scan-results-dlq"]
  }
  statement {
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = ["arn:aws:sqs:${var.region}:${var.account_id}:cue-scan-results-queue"]
  }
 }

# --- Policies for Glue and Archive Roles (Restored) ---

data "aws_iam_policy_document" "glue_job_policy" {
  # This policy should contain the permissions needed for your Glue job
  # Example permissions:
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]
    resources = [
      "arn:aws:s3:::${var.cue_archive_bucket}/*"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "glue:GetConnection",
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface"
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "glue_crawler_policy" {
  # Permissions needed for the Glue crawler
  statement {
    effect = "Allow"
    actions = [
      "glue:*"
    ]
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]
    resources = [
      "arn:aws:s3:::${var.cue_archive_bucket}/*"
    ]
  }
}

# --- Policy for EventBridge Lambda Scheduler ---

data "aws_iam_policy_document" "eventbridge_lambda_scheduler_policy" {
  statement {
    effect = "Allow"
    actions = ["lambda:InvokeFunction"]
    resources = [
      "arn:aws:lambda:${var.region}:${var.account_id}:function:cue_notification_manager",
      "arn:aws:lambda:${var.region}:${var.account_id}:function:cue_cleanup_uploads",
    ]
  }
}