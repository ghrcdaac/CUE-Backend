# ==============================================================================
# File: terraform/archive/outputs.tf (Corrected)
# ==============================================================================

output "metrics_crawler_arn"{
    value = aws_glue_crawler.metrics_crawler.arn
}

output "archive_database_arn"{
    value = aws_glue_catalog_database.cue_archive_database.arn
}

output "archive_metrics_table_arn"{
    value = aws_glue_catalog_table.metrics.arn
}

output "athena_eventbridge_rule_arn"{
    value = aws_cloudwatch_event_rule.athena_query_rule.arn
}