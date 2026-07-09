variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "ap-southeast-2"
}

variable "bucket_name" {
  description = "Name of the S3 bucket for static site files"
  type        = string
  default     = "tasmanian-grid-frontend-aemo"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "Prod"
}

variable "tags" {
  type = map(string)
  default = {
    Name = "tasmanian-grid-frontend-aemo"
    Environment = "Prod"
  }
  
}

variable "default_ttl" {
  description = "Default TTL (in seconds) for CloudFront cache"
  type        = number
  default     = 60
}

variable "max_ttl" {
  description = "Maximum TTL (in seconds) for CloudFront cache"
  type        = number
  default     = 86400
}


variable "domain_name" {
  default = "varun.example.com"
}