resource "aws_s3_object" "glue_job_script" {
    bucket = var.cue_archive_bucket 
    key    = "/scripts/age_off_metrics_job.py"
    source = "../src/python/glue_jobs/age_off_metrics_job.py"
    content_type = "text/x-python"
}

resource "aws_glue_job" "cue_age_off_metrics_job" {
    name         = "age_off_metrics"
    glue_version = "5.0"
    role_arn     = var.cue_glue_job_role_arn
    max_capacity = 0.0625
    max_retries  = 0
    timeout      = 10
    connections = [aws_glue_connection.cue_db_connection.name]

    command {
        name            = "pythonshell"
        script_location = "s3://${var.cue_archive_bucket}/scripts/age_off_metrics_job.py"
        python_version  = "3.9"
    }

    default_arguments = {
        "--DB_HOST"                   = var.db_host
        "--DB_PORT"                   = var.db_port
        "--DB_DATABASE"               = var.db_database
        "--DB_USER"                   = var.db_user
        "--DB_PASSWORD"               = var.db_password
        "--SSM_PARAM_NAME"            = var.metric_retention_period_name
        "--ARCHIVE_BUCKET"            = var.cue_archive_bucket
        "library-set"                 = "analytics"
        "--additional-python-modules" = "psycopg2-binary"
    }
}

resource "aws_glue_trigger" "age_off_metrics_trigger" {
    name     = "metrics_age_off_trigger"
    type     = "SCHEDULED" 
    schedule = "cron(0 3 ? * SUN *)" 
    actions {
        job_name =  aws_glue_job.cue_age_off_metrics_job.name
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
    availability_zone = var.availability_zone 
    security_group_id_list = var.security_group_ids
    subnet_id              = var.subnet_id
  }
}