# ==============================================================================
# File: terraform/glue/policies.tf
# Purpose: Defines IAM policies required by the Glue module.
# ==============================================================================

# --- Assume Role Policy (Trust Policy) for the Glue Service ---
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

# --- Permissions Policy for the Glue Job ---
data "aws_iam_policy_document" "cue_glue_job_policy" {
  # RDS Database Access
  statement {
    effect    = "Allow"
    actions   = ["rds-data:ExecuteStatement"]
    resources = ["arn:aws:rds:${var.region}:${var.account_id}:cluster:${var.rds_cluster_identifier}"]
  }

  # SSM Parameter Store Access
  statement {
    effect    = "Allow"
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:${var.region}:${var.account_id}:parameter/${var.metric_retention_period_name}"]
  }

  # S3 Archive Bucket Access
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:DeleteObject"
    ]
    resources = [
      "arn:aws:s3:::${var.cue_archive_bucket}",
      "arn:aws:s3:::${var.cue_archive_bucket}/*"
    ]
  }

  # CloudWatch Logging Permissions
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:*:*:/aws-glue/jobs/*"]
  }

  # S3 File Report Bucket Access
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:DeleteObject",
      "s3:PutObjectTagging"
    ]
    resources = [
      "arn:aws:s3:::${var.file_report_bucket}",
      "arn:aws:s3:::${var.file_report_bucket}/*"
    ]
  }

  # SES Email Access
  statement {
    effect = "Allow"
    actions = [
      "ses:SendEmail",
      "ses:SendRawEmail"
    ]
    resources = ["*"]
  }
}

