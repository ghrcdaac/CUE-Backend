
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



# glue job Role
resource "aws_iam_role" "cue_glue_job_role" {
  name               = "CUEGlueJobRole"
  assume_role_policy = local.cue_glue_job_assume_role_rendered 
}

resource "aws_iam_policy" "cue_glue_job_policy" {
  name        = "CUEGlueJobPolicy"
  description = "Policy granting permission to CUE Glue job"
  policy      = local.cue_glue_job_policy_rendered 
}

resource "aws_iam_role_policy_attachment" "cue_glue_job_role_attach" {
  role = aws_iam_role.cue_glue_job_role.name 
  policy_arn = aws_iam_policy.cue_glue_job_policy.arn

}

# archive api lambda Role
resource "aws_iam_role" "cue_archive_api_lambda_role" {
  name               = "CUEArchiveApiLambdaRole"
  assume_role_policy = local.cue_archive_api_lambda_assume_role_rendered 
}

resource "aws_iam_role_policy" "cue_archive_api_lambda_policy" {
  name   = "CUEArchiveApiLambdaPolicy"
  role   = aws_iam_role.cue_archive_api_lambda_role.id
  policy = local.cue_archive_api_lambda_policy_rendered 
}

resource "aws_iam_role_policy_attachment" "cue_archive_api_lambda_execution_role_attach" {
  role       = aws_iam_role.cue_archive_api_lambda_role.id
  policy_arn = var.lambda_execution_policy_arn
}

# glue crawler Role
resource "aws_iam_role" "cue_crawler_role" {
  name               = "CUECrawlerRole"
  assume_role_policy = local.cue_crawler_assume_role_rendered 
}

resource "aws_iam_policy" "cue_crawler_policy" {
  name        = "CUECrawlerPolicy"
  description = "Policy granting permission to CUE Glue Crawler"
  policy      = local.cue_crawler_policy_rendered 
}

resource "aws_iam_role_policy_attachment" "cue_crawler_role_attach" {
  role = aws_iam_role.cue_crawler_role.name 
  policy_arn = aws_iam_policy.cue_crawler_policy.arn

}

