

#scan event lambda Role

resource "aws_iam_role" "cue_scan_event_role"{
    name                    = "CUEScanEventRole"
    assume_role_policy      = data.template_file.cue_scan_event_assume_role.rendered
}

resource "aws_iam_role_policy" "cue_scan_event_policy"{
    name    = "CUEScanEventPolicy"
    role    = aws_iam_role.cue_scan_event_role.id
    policy  = data.template_file.cue_scan_event_policy.rendered
}

resource "aws_iam_role_policy_attachment" "cue_scan_event_execution_role_attach" {
    role        = aws_iam_role.cue_scan_event_role.id
    policy_arn  = var.lambda_execution_policy_arn
}

# api lambda Role

resource "aws_iam_role" "cue_api_lambda_role"{
    name                    = "CUEApiLambdaRole"
    assume_role_policy      = data.template_file.cue_api_lambda_assume_role.rendered
}

resource "aws_iam_role_policy" "cue_api_lambda_policy" {
    name    = "CUEApiLambdaPolicy"
    role    = aws_iam_role.cue_api_lambda_role.id
    policy  = data.template_file.cue_api_lambda_policy.rendered
}

resource "aws_iam_role_policy_attachment" "cue_api_lambda_execution_role_attach" {
    role            = aws_iam_role.cue_api_lambda_role.id
    policy_arn      = var.lambda_execution_policy_arn
}