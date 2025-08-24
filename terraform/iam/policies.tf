# ./terraform/iam/policies.tf

data "aws_iam_policy_document" "cue_scan_event_policy" {
  statement {
    effect = "Allow"
    actions = ["events:PutEvents"]
    resources = [var.event_bus_arn]
  }
  statement {
    effect = "Allow"
    actions = ["sqs:SendMessage"]
    resources = [var.cue_clean_sqs_queue_arn]
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

data "aws_iam_policy_document" "infected_notification_scheduler_policy" {
  statement {
    effect = "Allow"
    actions = ["lambda:InvokeFunction"]
    resources = [var.notification_manager_lambda_arn]
  }
}

data "aws_iam_policy_document" "file_transfer_policy" {
  statement {
    effect = "Allow"
    actions = ["s3:GetObject","s3:GetObjectTagging"]
    resources = ["arn:aws:s3:::${var.cue_staging_bucket}/*"]
  }
  statement {
    effect = "Allow"
    actions = ["s3:PutObject","s3:PutObjectTagging","s3:PutObjectAcl"]
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility"]
    resources = ["*"]
  }
}