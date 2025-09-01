output "db_user" {
  value = data.aws_rds_cluster.cue_rds.master_username
}

output "db_host" {
  value = data.aws_rds_cluster.cue_rds.endpoint
}

output "db_database" {
  value = data.aws_rds_cluster.cue_rds.database_name
}

output "db_port" {
  value = data.aws_rds_cluster.cue_rds.port
}

output "db_proxy_host" {
  description = "The endpoint of the RDS Proxy."
  value       = aws_db_proxy.cue_proxy.endpoint
}

