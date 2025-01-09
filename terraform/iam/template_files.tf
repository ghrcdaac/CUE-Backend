

data "template_file" "cue_scan_event_assume_role" {
    template = file("./iam/cue_scan_event_assume_role.json")
    vars = {
        region = var.region
        account_id = var.account_id
    }
}

data "template_file" "cue_scan_event_policy" {
    template = file("./iam/cue_scan_event_policy.json")
    
    vars = {
        region = var.region
        account_id = var.account_id
        cue_css_scan_sns_arn = var.cue_css_scan_sns_arn
    }
}
