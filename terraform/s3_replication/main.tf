
resource "aws_s3_bucket" "replication_test_bucket" {
  bucket = var.cue_replication_dest_test_bucket 
}


resource "aws_s3_bucket" "cue_manifest_report_bucket" {
  bucket = var.cue_manifest_report_bucket
}

resource "aws_s3_object" "manifest_folder" {
  bucket = aws_s3_bucket.cue_manifest_report_bucket.id
  key    = "manifest/"
}

resource "aws_s3_object" "report_folder" {
  bucket = aws_s3_bucket.cue_manifest_report_bucket.id
  key    = "report/"
}

resource "aws_s3_bucket_lifecycle_configuration" "staging_bucket_lifecycle_configuration" {
  bucket = var.cue_staging_bucket 

  rule {
    id = "expire-after-30-days"
    expiration {
      days = 30
    } 
    filter {object_size_greater_than = 1}
      
    status = "Disabled" # enable later
  }
}

resource "aws_s3_bucket_versioning" "replication_test_bucket_versioning" {
  bucket = aws_s3_bucket.replication_test_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "replication_test_bucket_access" {
  bucket = aws_s3_bucket.replication_test_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_replication_configuration" "staging_bucket_replication_configuration"{
    depends_on = [ aws_s3_bucket_versioning.replication_test_bucket_versioning ]
    role = var.cue_replication_role_arn
    bucket = var.cue_staging_bucket
    rule {
        id = "Rule_0"
        status = "Enabled"
        filter {}
        delete_marker_replication {
          status = "Disabled"
        }
        destination {
          access_control_translation{
              owner = "Destination"
          }
          replication_time {
            status = "Enabled"
            time {
              minutes = 15
            } 
          }
          metrics {
            status = "Enabled"
            event_threshold {
              minutes = 15
            }
          }
          account = var.account_id
          bucket = aws_s3_bucket.replication_test_bucket.arn 
          storage_class = "STANDARD"
        }
    }
}
