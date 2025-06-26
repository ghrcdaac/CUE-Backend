# ./terraform/lambda/ses.tf

# --- IAM Role for email_sender Lambda ---
# This role and its policy are now defined here, alongside the Lambda that uses them.
resource "aws_iam_role" "email_sender_role" {
  name               = "CUEEmailSenderRole"
  assume_role_policy = file("${path.module}/../iam/cue_scan_event_assume_role.json")
}

# This policy grants the necessary permission to send emails via SES.
resource "aws_iam_role_policy" "email_sender_ses_policy" {
  name = "CUEEmailSenderSESPolicy"
  role = aws_iam_role.email_sender_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Action    = ["ses:SendEmail", "ses:SendRawEmail"],
      # Resource must be "*" for ses:SendEmail as required by AWS.
      Resource  = ["*"]
    }]
  })
}


# --- Email Sender Lambda ---
# This function's only job is to send emails via SES.
resource "aws_lambda_function" "email_sender" {
  filename         = "../artifacts/email-sender-lambda.zip"
  function_name    = "cue_email_sender"
  # This now correctly references the role created in this same file.
  role             = aws_iam_role.email_sender_role.arn
  handler          = "email_sender.handler.handler"
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  source_code_hash = filesha256("../artifacts/email-sender-lambda.zip")
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      SENDER_EMAIL           = var.sender_email
      SOURCE_ARN             = var.ses_source_arn
      CONFIGURATION_SET_NAME = var.ses_configuration_set_name
      SES_REGION             = var.ses_region
      LOG_LEVEL              = "INFO"
    }
  }
}
