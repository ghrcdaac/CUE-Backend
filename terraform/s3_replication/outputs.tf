output staging_bucket_replication_configuration_id{
    description = "ID of s3 replication configuration on the staging bucket"
    value = aws_s3_bucket_replication_configuration.staging_bucket_replication_configuration.id
}