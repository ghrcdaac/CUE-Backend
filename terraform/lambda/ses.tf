# ==============================================================================
# File: terraform/lambda/ses.tf (V2 Refactored)
# Purpose: Defines the email_sender Lambda and its specific IAM Role.
# ==============================================================================

# --- Assume Role Policy Document for Lambda ---
# This defines the trust relationship allowing the Lambda service to assume this role.
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

# --- Permissions Policy Document for the Email Sender ---
# This defines what the email_sender Lambda is allowed to do.
data "aws_iam_policy_document" "email_sender_policy" {
  statement {
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    # SES requires a wildcard resource for this action.
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface"
    ]
    resources = ["*"]
  }
}


# --- IAM Role for email_sender Lambda ---
resource "aws_iam_role" "email_sender_role" {
  name               = "CUEEmailSenderRole-v2"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
}

# --- IAM Policy Attachment ---
resource "aws_iam_role_policy" "email_sender_ses_policy" {
  name   = "CUEEmailSenderSESPolicy-v2"
  role   = aws_iam_role.email_sender_role.id
  policy = data.aws_iam_policy_document.email_sender_policy.json
}


# --- Email Sender Lambda ---
# This function's only job is to send emails via SES.
resource "aws_lambda_function" "email_sender" {
  # This references the archive_file resource defined in main.tf
  filename         = "../artifacts/email-sender-lambda.zip"
  source_code_hash = filebase64sha256("../artifacts/email-sender-lambda.zip")
  function_name    = "cue_email_sender"
  role             = aws_iam_role.email_sender_role.arn
  handler          = "handler.handler"
  runtime          = "python3.13" # Updated runtime
  architectures    = ["x86_64"]   # Added architecture

  timeout     = 60
  memory_size = 128

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  environment {
    variables = {
      SENDER_EMAIL           = var.sender_email
      SOURCE_ARN             = var.ses_source_arn
      CONFIGURATION_SET_NAME = var.ses_configuration_set_name
      SES_REGION             = var.ses_region
      LOG_LEVEL              = "INFO"
      REDEPLOY_TRIGGER = "1"
    }
  }
}

