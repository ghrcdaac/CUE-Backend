# scan event lambda Role
resource "aws_iam_role" "cue_scan_event_role" {
  name               = "CUEScanEventRole"
  assume_role_policy = local.cue_scan_event_assume_role_rendered 
}

resource "aws_iam_role_policy" "cue_scan_event_policy" {
  name   = "CUEScanEventPolicy"
  role   = aws_iam_role.cue_scan_event_role.id
  policy = local.cue_scan_event_policy_rendered 
}

resource "aws_iam_role_policy_attachment" "cue_scan_event_execution_role_attach" {
  role       = aws_iam_role.cue_scan_event_role.id
  policy_arn = var.lambda_execution_policy_arn
}

# api lambda Role
resource "aws_iam_role" "cue_api_lambda_role" {
  name               = "CUEApiLambdaRole"
  assume_role_policy = local.cue_api_lambda_assume_role_rendered 
}

resource "aws_iam_role_policy" "cue_api_lambda_policy" {
  name   = "CUEApiLambdaPolicy"
  role   = aws_iam_role.cue_api_lambda_role.id
  policy = local.cue_api_lambda_policy_rendered 
}

resource "aws_iam_role_policy_attachment" "cue_api_lambda_execution_role_attach" {
  role       = aws_iam_role.cue_api_lambda_role.id
  policy_arn = var.lambda_execution_policy_arn
}

# glue job Role
resource "aws_iam_role" "cue_glue_job_role" {
  name               = "CUEGlueJobRole"
  assume_role_policy = local.cue_glue_job_assume_role_rendered 
}

resource "aws_iam_policy" "cue_glue_job_policy" {
  name        = "CUEGlueJobPolicy"
  description = "Policy granting permission to CUE Glue job"
  policy      = local.cue_glue_job_policy_rendered 
}

resource "aws_iam_role_policy_attachment" "cue_glue_job_role_attach" {
  role = aws_iam_role.cue_glue_job_role.name 
  policy_arn = aws_iam_policy.cue_glue_job_policy.arn
}