# ./terraform/iam/main.tf

# --- CUE Scan Event Lambda Role ---
resource "aws_iam_role" "cue_scan_event_role" {
  name               = "CUEScanEventRole"
  assume_role_policy = file("${path.module}/cue_scan_event_assume_role.json")

  lifecycle {
    prevent_destroy = true
    # This tells Terraform to not worry if the tags on the live resource
    # are different from what's defined here. This prevents the
    # ConcurrentModification error caused by fighting over tags.
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_iam_role_policy_attachment" "cue_scan_event_vpc" {
  role       = aws_iam_role.cue_scan_event_role.id
  policy_arn = var.lambda_execution_policy_arn
}

resource "aws_iam_role_policy_attachment" "cue_scan_event_sqs" {
  role       = aws_iam_role.cue_scan_event_role.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

resource "aws_iam_role_policy" "cue_scan_event_policy" {
  name   = "CUEScanEventPolicy"
  role   = aws_iam_role.cue_scan_event_role.id
  policy = data.aws_iam_policy_document.cue_scan_event_policy.json
}

# --- CUE API Lambda Role ---
resource "aws_iam_role" "cue_api_lambda_role" {
  name               = "CUEApiLambdaRole"
  assume_role_policy = file("${path.module}/cue_api_lambda_assume_role.json")

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [tags, tags_all]
  }
}

resource "aws_iam_role_policy_attachment" "cue_api_lambda_vpc" {
  role       = aws_iam_role.cue_api_lambda_role.id
  policy_arn = var.lambda_execution_policy_arn
}

resource "aws_iam_role_policy" "cue_api_lambda_policy" {
  name   = "CUEApiLambdaPolicy"
  role   = aws_iam_role.cue_api_lambda_role.id
  policy = file("${path.module}/cue_api_lambda_policy.json")
}

# --- Notification Manager Lambda Role ---
resource "aws_iam_role" "notification_manager_role" {
  name               = "CUENotificationManagerRole"
  assume_role_policy = file("${path.module}/cue_scan_event_assume_role.json")

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [tags, tags_all]
  }
}

resource "aws_iam_role_policy_attachment" "notification_manager_vpc" {
  role       = aws_iam_role.notification_manager_role.id
  policy_arn = var.lambda_execution_policy_arn
}

resource "aws_iam_role_policy" "notification_manager_policy" {
  name   = "CUENotificationManagerPolicy"
  role   = aws_iam_role.notification_manager_role.id
  policy = data.aws_iam_policy_document.notification_manager_policy.json
}

# --- Email Sender Lambda Role ---
resource "aws_iam_role" "email_sender_role" {
  name               = "CUEEmailSenderRole"
  assume_role_policy = file("${path.module}/cue_scan_event_assume_role.json")

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [tags, tags_all]
  }
}

resource "aws_iam_role_policy" "email_sender_policy" {
  name   = "CUEEmailSenderPolicy"
  role   = aws_iam_role.email_sender_role.id
  policy = data.aws_iam_policy_document.email_sender_policy.json
}
