# ./terraform/glue/s3.tf

# This resource creates the S3 bucket that will store the Glue job scripts and archived data.
resource "aws_s3_bucket" "cue_archive_bucket" {
  bucket = var.cue_archive_bucket

  # It's a best practice to explicitly block all public access.
  lifecycle {
    prevent_destroy = true
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
