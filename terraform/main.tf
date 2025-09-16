terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }

  }
}

provider "aws" {
  region = var.region
}

# --- Central S3 Archive Bucket ---
# This bucket is used by Glue, Athena, and IAM, so it's defined here at the root.
resource "aws_s3_bucket" "cue_archive_bucket" {
  bucket = var.cue_archive_bucket

  lifecycle {
    prevent_destroy = true
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_s3_bucket_public_access_block" "cue_archive_bucket_access" {
  bucket = aws_s3_bucket.cue_archive_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "cue_archive_bucket_versioning" {
  bucket = aws_s3_bucket.cue_archive_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cue_archive_bucket_encryption" {
  bucket = aws_s3_bucket.cue_archive_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# --- Central S3 Results Bucket ---
# This bucket is used by Athena and the process-athena-query Lambda
resource "aws_s3_bucket" "cue_archive_results_bucket" {
  bucket = var.cue_archive_results_bucket

  lifecycle {
    prevent_destroy = true
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_s3_bucket_public_access_block" "cue_archive_results_bucket_access" {
  bucket = aws_s3_bucket.cue_archive_results_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "cue_archive_results_bucket_versioning" {
  bucket = aws_s3_bucket.cue_archive_results_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cue_archive_results_bucket_encryption" {
  bucket = aws_s3_bucket.cue_archive_results_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}


# --- Other root resources ---
resource "aws_ssm_parameter" "metric_retention_period" {
  name  = var.metric_retention_period_name
  type  = "String"
  value = var.metric_retention_period_value
}