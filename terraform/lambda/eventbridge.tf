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
