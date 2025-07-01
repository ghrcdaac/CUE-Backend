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

# archive api lambda Role
resource "aws_iam_role" "cue_archive_api_lambda_role" {
  name               = "CUEArchiveApiLambdaRole"
  assume_role_policy = local.cue_archive_api_lambda_assume_role_rendered 
}

resource "aws_iam_role_policy" "cue_archive_api_lambda_policy" {
  name   = "CUEArchiveApiLambdaPolicy"
  role   = aws_iam_role.cue_archive_api_lambda_role.id
  policy = local.cue_archive_api_lambda_policy_rendered 
}

resource "aws_iam_role_policy_attachment" "cue_archive_api_lambda_execution_role_attach" {
  role       = aws_iam_role.cue_archive_api_lambda_role.id
  policy_arn = var.lambda_execution_policy_arn
}

# glue crawler Role
resource "aws_iam_role" "cue_crawler_role" {
  name               = "CUECrawlerRole"
  assume_role_policy = local.cue_crawler_assume_role_rendered 
}

resource "aws_iam_policy" "cue_crawler_policy" {
  name        = "CUECrawlerPolicy"
  description = "Policy granting permission to CUE Glue Crawler"
  policy      = local.cue_crawler_policy_rendered 
}

resource "aws_iam_role_policy_attachment" "cue_crawler_role_attach" {
  role = aws_iam_role.cue_crawler_role.name 
  policy_arn = aws_iam_policy.cue_crawler_policy.arn

}