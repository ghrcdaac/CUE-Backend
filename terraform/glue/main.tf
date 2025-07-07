# ./terraform/glue/main.tf

# This resource uploads the Python script to the S3 bucket created in s3.tf.
resource "aws_s3_object" "glue_job_script" {
  # Reference the bucket created in this module.
  bucket = aws_s3_bucket.cue_archive_bucket.id
  # Removed the leading slash from the key for S3 best practices.
  key          = "scripts/age_off_metrics_job.py"
  source       = "../src/python/glue_jobs/age_off_metrics_job.py"
  content_type = "text/x-python"

  # This ensures the bucket is created before Terraform attempts to upload the file.
  depends_on = [aws_s3_bucket.cue_archive_bucket]
}

resource "aws_glue_job" "cue_age_off_metrics_job" {
  name         = "age_off_metrics"
  glue_version = "5.0" 
  role_arn     = var.cue_glue_job_role_arn
  max_capacity = 0.0625
  max_retries  = 0
  timeout      = 10
  connections  = [aws_glue_connection.cue_db_connection.name]

  command {
    name            = "pythonshell"
    # Reference the bucket created in this module for the script location.
    script_location = "s3://${aws_s3_bucket.cue_archive_bucket.id}/scripts/age_off_metrics_job.py"
    python_version  = "3.9"
  }

  default_arguments = {
    "--DB_HOST"                   = var.db_host
    "--DB_PORT"                   = var.db_port
    "--DB_DATABASE"               = var.db_database
    "--DB_USER"                   = var.db_user
    "--DB_PASSWORD"               = var.db_password
    "--SSM_PARAM_NAME"            = var.metric_retention_period_name
    # Reference the bucket created in this module.
    "--ARCHIVE_BUCKET"            = aws_s3_bucket.cue_archive_bucket.id
    "--library-set"               = "analytics"
    "--additional-python-modules" = "psycopg2-binary"
  }
}

resource "aws_glue_trigger" "age_off_metrics_trigger" {
  name     = "metrics_age_off_trigger"
  type     = "SCHEDULED"
  schedule = "cron(0 3 ? * SUN *)" # Runs every Sunday at 3:00 AM UTC

  actions {
    job_name = aws_glue_job.cue_age_off_metrics_job.name
  }
}

resource "aws_glue_connection" "cue_db_connection" {
  connection_properties = {
    JDBC_CONNECTION_URL = "jdbc:postgresql://${var.db_host}:${var.db_port}/${var.db_database}"
    PASSWORD            = var.db_password
    USERNAME            = var.db_user
  }

  name = "cue_db_connection"

  physical_connection_requirements {
    availability_zone      = var.availability_zone
    security_group_id_list = var.security_group_ids
    subnet_id              = var.subnet_id
  }
}
