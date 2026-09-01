# ==============================================================================
# File: terraform/glue/main.tf (V2 Refactored)
# Purpose: Defines the Glue job, trigger, connection, and its own IAM Role.
# ==============================================================================

# --- IAM Role for the Glue Job ---
# This role is defined here, alongside the job that uses it, making the module self-contained.
resource "aws_iam_role" "cue_glue_job_role" {
  name               = "CUEGlueJobRole-v2"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role_policy.json
}

resource "aws_iam_role_policy_attachment" "glue_service_role_attachment" {
  role       = aws_iam_role.cue_glue_job_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "cue_glue_job_policy" {
  name   = "CUEGlueJobPolicy-v2"
  role   = aws_iam_role.cue_glue_job_role.id
  policy = data.aws_iam_policy_document.cue_glue_job_policy.json
}

# --- Glue Resources ---

# This resource uploads the Python script for the Glue job to S3.
resource "aws_s3_object" "glue_job_script" {
  bucket       = var.cue_archive_bucket
  key          = "scripts/age_off_metrics_job.py"
  source       = "../src/python/glue_jobs/age_off_metrics_job.py"
  content_type = "text/x-python"
  etag         = filemd5("../src/python/glue_jobs/age_off_metrics_job.py")
}

# This defines the Glue job that archives old metrics.
resource "aws_glue_job" "cue_age_off_metrics_job" {
  name           = "age_off_metrics"
  glue_version   = "5.0"
  role_arn       = aws_iam_role.cue_glue_job_role.arn # Use the role created in this module
  max_capacity   = 0.0625
  max_retries    = 0
  timeout        = 10
  connections    = [aws_glue_connection.cue_db_connection.name]

  command {
    name            = "pythonshell"
    script_location = "s3://${var.cue_archive_bucket}/scripts/age_off_metrics_job.py"
    python_version  = "3.9"
  }

  default_arguments = {
    "--PG_HOST"                   = var.db_proxy_host
    "--PG_PORT"                   = var.db_port
    "--PG_DB"                     = var.db_database
    "--PG_USER"                   = var.db_user
    "--PG_PASS"                   = var.db_password
    "--SSM_PARAM_NAME"            = var.metric_retention_period_name
    "--ARCHIVE_BUCKET"            = var.cue_archive_bucket
    "--library-set"               = "analytics"
    "--additional-python-modules" = "asyncpg,structlog"
  }
}

# This trigger runs the Glue job on a weekly schedule.
resource "aws_glue_trigger" "age_off_metrics_trigger" {
  name     = "metrics_age_off_trigger"
  type     = "SCHEDULED"
  schedule = "cron(0 3 ? * SUN *)" # Runs every Sunday at 3:00 AM UTC

  actions {
    job_name = aws_glue_job.cue_age_off_metrics_job.name
  }
}

# This defines the VPC connection for the Glue job to access the database.
resource "aws_glue_connection" "cue_db_connection" {
  connection_properties = {
    JDBC_CONNECTION_URL = "jdbc:postgresql://${var.db_proxy_host}:${var.db_port}/${var.db_database}"
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

# This resource uploads the Python script for the PDF report generator Glue job to S3.
resource "aws_s3_object" "file_status_report_job_script" {
  bucket       = var.cue_archive_bucket
  key          = "scripts/file_status_report_job.py"
  source       = "../src/python/glue_jobs/file_status_report_job.py"
  content_type = "text/x-python"
  etag         = filemd5("../src/python/glue_jobs/file_status_report_job.py")
}

# This defines the Glue job that generates the file status PDF reports.
resource "aws_glue_job" "cue_file_status_report_job" {
  name           = "file_status_report_generator"
  glue_version   = "5.0"
  role_arn       = aws_iam_role.cue_glue_job_role.arn
  max_capacity   = 0.0625
  max_retries    = 0
  timeout        = 30 # Allow up to 30 minutes for large reports
  connections    = [aws_glue_connection.cue_db_connection.name]

  command {
    name            = "pythonshell"
    script_location = "s3://${var.cue_archive_bucket}/scripts/file_status_report_job.py"
    python_version  = "3.9"
  }

  default_arguments = {
    "--PG_HOST"                   = var.db_proxy_host
    "--PG_PORT"                   = var.db_port
    "--PG_DB"                     = var.db_database
    "--PG_USER"                   = var.db_user
    "--PG_PASS"                   = var.db_password
    "--FILE_REPORT_BUCKET"        = var.file_report_bucket
    "--SENDER_EMAIL"              = var.sender_email
    "--SES_REGION"                = var.ses_region
    "--SES_SOURCE_ARN"            = var.ses_source_arn
    "--SES_CONFIGURATION_SET_NAME" = var.ses_configuration_set_name
    "--library-set"               = "analytics"
    "--additional-python-modules" = "asyncpg,structlog,reportlab,boto3"
  }
}

