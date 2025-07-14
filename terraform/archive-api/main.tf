
resource "aws_s3_bucket" "cue_archive_results_bucket"{
  bucket = var.cue_archive_results_bucket
} 

# Process Athena Query Lambda

resource "aws_lambda_function" "cue_process_athena_query"{
    filename                = "../artifacts/process-athena-query-lambda.zip"
    function_name           = "cue_process_athena_query"
    role                    = var.cue_archive_api_lambda_role_arn 
    handler                 = "process_athena_query.handler.handler"
    runtime                 = "python3.13"
    architectures           = ["arm64"]
    source_code_hash        = filesha256("../artifacts/process-athena-query-lambda.zip")
    timeout                 = 180

    environment {
      variables = {
        RESULTS_BUCKET = var.cue_archive_results_bucket
      }
    }

    vpc_config {
        subnet_ids          = var.subnet_ids
        security_group_ids  = var.security_group_ids
    }
}

# Athena (glue database)

resource "aws_glue_catalog_database" "cue_archive_database" {
  name = var.cue_archive_database_name 
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
    location = "s3://${var.cue_archive_bucket}/data/metrics/"  
    input_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name = "parquet"
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
      type  = "timestamp"
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

resource "aws_glue_crawler" "metrics_crawler" {
  name          = "metrics-crawler"
  role          = var.cue_crawler_role_arn
  database_name = aws_glue_catalog_database.cue_archive_database.name
  schedule = "cron(30 3 ? * SUN *)" 
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
  name          = "athena-query-status-rule"
  description   = "Rule to capture Athena query status changes"
  event_pattern = jsonencode({
    "source": ["aws.athena"],
    "detail-type": ["Athena Query State Change"],
    "detail": {
      "currentState":["SUCCEEDED", "FAILED"]
    }
  })
}

resource "aws_cloudwatch_event_target" "cue_process_athena_query_lambda_target" {
  rule      = aws_cloudwatch_event_rule.athena_query_rule.name
  arn       = aws_lambda_function.cue_process_athena_query.arn
}

resource "aws_lambda_permission" "athena_rule_permission" {
  statement_id    = "AllowExecutionFromEventBridge"
  action          = "lambda:InvokeFunction"
  function_name   = aws_lambda_function.cue_process_athena_query.function_name
  principal       = "events.amazonaws.com"
  source_arn      = aws_cloudwatch_event_rule.athena_query_rule.arn
}