terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.95.0"  
    }
  }
}

provider "aws" {
    region      = var.region

}

resource "aws_ssm_parameter" "metric_retention_period" {
    name  = var.metric_retention_period_name 
    type  = "String"
    value = var.metric_retention_period_value
}

resource "aws_s3_bucket" "cue_archive_bucket"{
    bucket = var.cue_archive_bucket
}