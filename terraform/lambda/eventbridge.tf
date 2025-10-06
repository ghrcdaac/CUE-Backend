# ==============================================================================
# File: terraform/lambda/eventbridge.tf (V2 Refactored)
# Purpose: Defines the central EventBridge bus and all rules/targets.
# ==============================================================================

# --- EventBridge Bus ---
# A central EventBridge bus for all CUE application events.
resource "aws_cloudwatch_event_bus" "cue_app_bus" {
  name = "cue-application-bus"
}

# --- Event Rules & Targets ---

# Rule to capture all application events from the API and scanner
resource "aws_cloudwatch_event_rule" "application_events_rule" {
  name           = "cue-application-events-rule"
  description    = "Routes all CUE application events."
  event_bus_name = aws_cloudwatch_event_bus.cue_app_bus.name

  event_pattern = jsonencode({
    source = ["com.cue.api", "com.cue.scanner"]
  })
}

# Target for the above rule: the notification_manager Lambda
resource "aws_cloudwatch_event_target" "notification_manager_target" {
  rule           = aws_cloudwatch_event_rule.application_events_rule.name
  target_id      = "TriggerNotificationManager"
  arn            = aws_lambda_function.notification_manager.arn
  event_bus_name = aws_cloudwatch_event_bus.cue_app_bus.name
}

# Rule to capture Athena query completion events
resource "aws_cloudwatch_event_rule" "athena_query_state_change_rule" {
  name        = "cue-athena-query-state-change-rule"
  description = "Triggers processor when an Athena query completes."

  event_pattern = jsonencode({
    source      = ["aws.athena"],
    "detail-type" = ["Athena Query State Change"]
  })
}

# Target for the Athena rule: the process_athena_query Lambda
# resource "aws_cloudwatch_event_target" "process_athena_query_target" {
#   rule      = aws_cloudwatch_event_rule.athena_query_state_change_rule.name
#   target_id = "TriggerAthenaQueryProcessor"
#   arn       = aws_lambda_function.process_athena_query.arn
# }


resource "aws_cloudwatch_event_rule" "cost_update_schedule" {
  name                = "cue-cost-update-lambda-schedule"
  description         = "Schedule to run cost update lambda"
  schedule_expression = "cron(0 1 * * ? *)"  
}

resource "aws_cloudwatch_event_target" "update_cost_target" {
  rule      = aws_cloudwatch_event_rule.cost_update_schedule.name
  target_id = "TriggerCostUpdate"
  arn       = aws_lambda_function.cue_cost_update.arn
}

resource "aws_scheduler_schedule" "infected_file_notification_schedule" {
  name = "cue_infected_file_notification_scheduler"
  flexible_time_window {
    mode = "OFF"
  }
  schedule_expression = "cron(*/30 * * * ? *)"
  target {
    role_arn = var.notification_manager_scheduler_role_arn
    arn = aws_lambda_function.notification_manager.arn
    input = replace(
      replace(
        jsonencode({
          "detail-type": "ScheduledInfectedFileNotification",
          "detail":"<aws.scheduler.scheduled-time>"
        }),"\\u003c", "<"),
        "\\u003e", ">"
    )
    retry_policy {
      maximum_event_age_in_seconds = 1800
      maximum_retry_attempts = 3
    }
  }
}

resource "aws_lambda_permission" "allow_eventbridge_scheduler_to_notification_manager" {
  statement_id  = "AllowExecutionFromEventBridgeScheduler"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notification_manager.function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.infected_file_notification_schedule.arn
}