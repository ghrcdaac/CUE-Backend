data "aws_rds_cluster" "cue_rds"{
    rds_cluster_identifier = var.rds_cluster_identifier
}