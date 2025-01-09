

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
