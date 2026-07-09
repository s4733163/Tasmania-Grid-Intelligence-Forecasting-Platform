output "cloudfront_url" {
  description = "URL to access the static site via CloudFront"
  value       = "https://${aws_cloudfront_distribution.static_site.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (useful for cache invalidation)"
  value       = aws_cloudfront_distribution.static_site.id
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket storing the static files"
  value       = aws_s3_bucket.static_site.id
}
