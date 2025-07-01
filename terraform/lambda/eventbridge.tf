# ./terraform/lambda/eventbridge.tf

# A central EventBridge bus for CUE application events.
resource "aws_cloudwatch_event_bus" "cue_app_bus" {
  name = "cue-application-bus"
}
