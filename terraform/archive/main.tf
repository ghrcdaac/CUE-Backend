# ==============================================================================
# File: terraform/archive-api/main.tf (Corrected)
# Purpose: Defines the Glue Data Catalog and Athena resources.
# NOTE: The aws_lambda_function and archive_file resources have been removed,
# as they are now correctly managed by the central 'lambda' module.
# ==============================================================================

# --- Athena (glue database) ---

resource "aws_glue_catalog_database" "cue_archive_database" {
  name        = var.cue_archive_database_name
  description = "This is the cue archive database"
}

resource "aws_glue_catalog_table" "metrics" {
  database_name = aws_glue_catalog_database.cue_archive_database.name
  name          = "metrics"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://${var.cue_archive_bucket}/data/metrics/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"

      parameters = {
        "serialization.format" = 1
      }
    }

    columns {
      name = "id"
      type = "string"
    }
    columns {
      name = "name"
      type = "string"
    }
    columns {
      name = "type"
      type = "string"
    }
    columns {
      name = "size_bytes"
      type = "int"
    }
    columns {
      name = "collection_path"
      type = "string"
    }
    columns {
      name = "edpub"
      type = "boolean"
    }
    columns {
      name = "checksum"
      type = "string"
    }
    columns {
      name = "upload_time"
      type = "timestamp"
    }
    columns {
      name = "scan_start"
      type = "timestamp"
    }
    columns {
      name = "scan_end"
      type = "timestamp"
    }
    columns {
      name = "egress_start"
      type = "timestamp"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "scan_results"
      type = "string"
    }
    columns {
      name = "ngroup_id"
      type = "string"
    }
    columns {
      name = "metric_upload_at"
      type = "timestamp" 
    }
    columns {
      name = "aws_transfer_cost"
      type = "decimal"
    }
    columns {
      name = "scanner_cost"
      type = "decimal"
    }
  }

  partition_keys {
    name = "date"
    type = "string"
  }
  partition_keys {
    name = "collection_id"
    type = "string"
  }
  partition_keys {
    name = "provider_id"
    type = "string"
  }
  partition_keys {
    name = "cueuser_uploaded"
    type = "string"
  }
}

resource "aws_iam_role" "cue_crawler_role" {
  name               = "CUECrawlerRole"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role_policy.json
}

resource "aws_iam_role_policy" "cue_crawler_role_policy" {
  role = aws_iam_role.cue_crawler_role.id
  policy = data.aws_iam_policy_document.cue_crawler_policy.json
}

resource "aws_glue_crawler" "metrics_crawler" {
  name          = "metrics-crawler"
  role          = aws_iam_role.cue_crawler_role.arn
  database_name = aws_glue_catalog_database.cue_archive_database.name
  schedule      = "cron(30 3 ? * SUN *)"

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  s3_target {
    path = "s3://${var.cue_archive_bucket}/data/metrics"
  }

  schema_change_policy {
    update_behavior = "LOG"
    delete_behavior = "LOG"
  }
}

resource "aws_cloudwatch_event_rule" "athena_query_rule" {
  name        = "athena-query-status-rule"
  description = "Rule to capture Athena query status changes"
  event_pattern = jsonencode({
    "source" : ["aws.athena"],
    "detail-type" : ["Athena Query State Change"],
    "detail" : {
      "currentState" : ["SUCCEEDED", "FAILED"]
    }
  })
}

resource "aws_cloudwatch_event_target" "cue_process_athena_query_lambda_target" {
  rule      = aws_cloudwatch_event_rule.athena_query_rule.name
  arn       = var.process_athena_query_lambda_arn
  target_id = "ProcessAthenaQueryLambdaTarget"
}

resource "aws_lambda_permission" "athena_rule_permission" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.process_athena_query_lambda_arn # Use the ARN directly
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.athena_query_rule.arn
}

