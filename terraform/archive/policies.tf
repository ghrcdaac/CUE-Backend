# ==============================================================================
# File: terraform/archive/policies.tf (New)
# Purpose: Defines IAM policies required by the Archive module.
# ==============================================================================

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

data "aws_iam_policy_document" "cue_crawler_policy" {
  # This policy is the HCL equivalent of your cue_crawler_policy.json
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.cue_archive_bucket}",
      "arn:aws:s3:::${var.cue_archive_bucket}/*"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:UpdateDatabase",
      "glue:GetTable",
      "glue:GetTables",
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:CreatePartition",
      "glue:BatchCreatePartition",
      "glue:UpdatePartition",
      "glue:BatchGetPartition"
    ]
    resources = [
      "arn:aws:glue:${var.region}:${var.account_id}:catalog",
      "arn:aws:glue:${var.region}:${var.account_id}:database/${var.cue_archive_database_name}",
      "arn:aws:glue:${var.region}:${var.account_id}:table/${var.cue_archive_database_name}/*"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws-glue/crawlers:log-stream:${aws_glue_crawler.metrics_crawler.name}"]
  }
}

