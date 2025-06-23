# ./terraform/iam/policies.tf

data "aws_iam_policy_document" "cue_scan_event_policy" {
  statement {
    effect = "Allow"
    actions = ["events:PutEvents"]
    resources = [var.event_bus_arn]
  }
}

data "aws_iam_policy_document" "notification_manager_policy" {
  statement {
    effect = "Allow"
    actions = ["lambda:InvokeFunction"]
    resources = [var.email_sender_lambda_arn]
  }
}

data "aws_iam_policy_document" "email_sender_policy" {
  statement {
    effect = "Allow"
    actions = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
}

