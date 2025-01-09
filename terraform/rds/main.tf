data "aws_rds_cluster" "cue_rds"{
    cluster_identifier = var.rds_cluster_identifier
}