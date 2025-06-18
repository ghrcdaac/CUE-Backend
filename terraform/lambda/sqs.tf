# ./terraform/lambda/sqs.tf

# --- SQS Queues for Buffering and Retries ---

# 1. Dead-Letter Queue (DLQ) to catch messages that fail repeatedly.
resource "aws_sqs_queue" "scan_results_dlq" {
  name = "cue-scan-results-dlq"
  # Keep failed messages for 14 days for inspection.
  message_retention_seconds = 1209600
}

# 2. Main SQS queue that will subscribe to the SNS topic.
resource "aws_sqs_queue" "scan_results_queue" {
  name = "cue-scan-results-queue"
  # How long SQS should hide a message after the Lambda receives it.
  # This should be longer than your Lambda's timeout.
  visibility_timeout_seconds = 120 

  # Configuration for the Dead-Letter Queue.
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.scan_results_dlq.arn
    # After 5 failed attempts, move the message to the DLQ.
    maxReceiveCount     = 5
  })
}

# 3. SQS Queue Policy to allow the foreign SNS topic to send messages to it.
# This is the key to the cross-account integration.
resource "aws_sqs_queue_policy" "scan_results_queue_policy" {
  queue_url = aws_sqs_queue.scan_results_queue.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = "*", # It's safe to use "*" because the Condition below scopes it down.
        Action    = "sqs:SendMessage",
        Resource  = aws_sqs_queue.scan_results_queue.arn,
        Condition = {
          # This condition ensures ONLY the specified SNS topic can send messages.
          ArnEquals = {
            "aws:SourceArn" = var.cue_css_scan_sns_arn
          }
        }
      }
    ]
  })
}
