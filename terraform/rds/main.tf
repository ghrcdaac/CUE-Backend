# Data source to look up your existing RDS cluster
data "aws_rds_cluster" "cue_rds" {
  cluster_identifier = var.rds_cluster_identifier
}

# --- AWS Secrets Manager to store DB credentials for the proxy ---
resource "aws_secretsmanager_secret" "db_credentials" {
  name = "${var.rds_cluster_identifier}-proxy-credentials"
}

resource "aws_secretsmanager_secret_version" "db_credentials_version" {
  secret_id     = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({

    username            = data.aws_rds_cluster.cue_rds.master_username
    password            = var.db_password
    engine              = "postgres"
    host                = data.aws_rds_cluster.cue_rds.endpoint
    port                = data.aws_rds_cluster.cue_rds.port
    dbClusterIdentifier = var.rds_cluster_identifier
  })
}
resource "aws_iam_role_policy" "db_proxy_secrets_policy" {
  name = "RDSProxySecretsManagerAccess"
  role = split("/", var.db_proxy_iam_role_arn)[1]
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "secretsmanager:GetSecretValue",
        Resource = aws_secretsmanager_secret.db_credentials.arn
      }
    ]
  })
}

# --- RDS Proxy Definition ---
resource "aws_db_proxy" "cue_proxy" {
  name                     = "${var.rds_cluster_identifier}-proxy"
  debug_logging            = false
  engine_family            = "POSTGRESQL"
  idle_client_timeout      = 1800
  require_tls              = true
  role_arn                 = var.db_proxy_iam_role_arn
  vpc_security_group_ids   = var.security_group_ids
  vpc_subnet_ids           = var.subnet_ids

  auth {
    auth_scheme = "SECRETS"
    secret_arn  = aws_secretsmanager_secret.db_credentials.arn
    iam_auth    = "DISABLED"
  }

  tags = {
    Name = "CUE-RDS-Proxy"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# --- Proxy Target Group ---
resource "aws_db_proxy_default_target_group" "default" {
  db_proxy_name = aws_db_proxy.cue_proxy.name

  connection_pool_config {
    connection_borrow_timeout    = 120
    max_connections_percent      = 100
    max_idle_connections_percent = 50
  }
}

# --- Proxy Target ---
resource "aws_db_proxy_target" "cluster" {
  db_cluster_identifier = data.aws_rds_cluster.cue_rds.id
  db_proxy_name         = aws_db_proxy.cue_proxy.name
  target_group_name     = aws_db_proxy_default_target_group.default.name
}

