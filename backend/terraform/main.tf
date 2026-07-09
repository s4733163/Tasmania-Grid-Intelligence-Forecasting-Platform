# ---------- S3 Bucket (private) ----------

# Creating the s3 bucket
# This requires the bucket name and the tags
# Main tags should be Name and Environment in which the bukcet is being created
resource "aws_s3_bucket" "static_site" {
  bucket = var.bucket_name

  tags = var.tags
}


# This is to make the bucket completely private
# Requires the bucket id and the blocking of all public access
# We set all the 4 params to true to make the private access
resource "aws_s3_bucket_public_access_block" "static_site" {
  bucket = aws_s3_bucket.static_site.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


# ---------- S3 Bucket Policy (allow CloudFront only) ----------

resource "aws_s3_bucket_policy" "static_site" {
  # bucket on which the policy is applied
  bucket = aws_s3_bucket.static_site.id

  # Will ensure that the cloudfront is created first then the policy is created
  # Policy needs both the bucket and the arn / resource that can access the bucket
  depends_on = [aws_cloudfront_distribution.static_site ]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"

        # Apply this permission to all objects inside the bucket
        Resource  = "${aws_s3_bucket.static_site.arn}/*" 

        Condition = {
          # Only the specific cloudfront with the specific ARN can access the bucket
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.static_site.arn
          }
        }
      }
    ]
  })
}
# ---------- Upload static files ----------

locals {
  content_types = {
    ".html" = "text/html"
    ".css"  = "text/css"
    ".js"   = "application/javascript"
    ".json" = "application/json"
    ".svg"  = "image/svg+xml"
    ".png"  = "image/png"
    ".jpg"  = "image/jpeg"
    ".jpeg" = "image/jpeg"
    ".ico"  = "image/x-icon"
    ".woff" = "font/woff"
    ".woff2" = "font/woff2"
  }
}

# The objects are created within the s3 bucket
# We specify the bucket where the object will be stored
# we used foreach to create multiple objects
# The object key/name must be unique for normal behviour
resource "aws_s3_object" "static_files" {
  for_each = fileset("${path.module}/../../frontend/Tasmanian-Grid-Frontend/dist", "**")

  bucket = aws_s3_bucket.static_site.id
  key    = each.value
  source = "${path.module}/../../frontend/Tasmanian-Grid-Frontend/dist/${each.value}"

  etag = filemd5("${path.module}/../../frontend/Tasmanian-Grid-Frontend/dist/${each.value}")

  content_type = lookup(
    local.content_types,
    regex("\\.[^.]+$", each.value),
    "application/octet-stream"
  )
}

# ---------- CloudFront OAC ----------

# This is the means of authentication
# Origin Access Control ensures that the s3 bucket recongises that
# this is a cloudfront  (authentication) after which ARN
# is used for checking if access is allowed (authorisation)
resource "aws_cloudfront_origin_access_control" "static_site" {
  name                              = "${var.bucket_name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ---------- CloudFront Distribution ----------

resource "aws_cloudfront_distribution" "static_site" {
  # Turns CloudFront on and serves index.html when user opens the root URL.
  enabled             = true
  default_root_object = "index.html"

  #aliases = [var.domain_name]

  # depends_on = [ aws_acm_certificate_validation.main ]
  # My origin/source is this S3 bucket.
  # We specify use the specific s3 to serve files 
  # We provide identity(oac) to securely access it
  origin {
    domain_name              = aws_s3_bucket.static_site.bucket_regional_domain_name
    origin_id                = aws_s3_bucket.static_site.id
    origin_access_control_id = aws_cloudfront_origin_access_control.static_site.id
  }

  # Use HTTPs instead of HTTP always
  # Only Get or Head can be used which is good for static files
  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = aws_s3_bucket.static_site.id
    viewer_protocol_policy = "redirect-to-https"

    compress = true

    # CloudFront will not forward query strings or cookies to S3. This improves caching.
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = var.default_ttl
    max_ttl     = var.max_ttl
  }

  # Anyone can access the cloudfront
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Uses the default CloudFront SSL certificate
   viewer_certificate {
    cloudfront_default_certificate = true
   }

  # We specify the certificate to be used
  # The custom one that we created
  #viewer_certificate {
  #  acm_certificate_arn      = aws_acm_certificate_validation.main.certificate_arn
  #  ssl_support_method       = "sni-only"
  #  minimum_protocol_version = "TLSv1.2_2021"
  #}

  tags = {
    Name        = "${var.bucket_name}-cdn"
    Environment = var.environment
  }
}


# Get a ssl certificate for the domain that I specified
# resource "aws_acm_certificate" "main" {
#  domain_name       = var.domain_name
#  validation_method = "DNS"

#  lifecycle {
#    create_before_destroy = true
#  }

#   tags = {
#     Environment = var.environment
#     ManagedBy   = "terraform"
#   }
# }
#
# # Look up the hosted zone
# data "aws_route53_zone" "main" {
#   name         = "example.com"
#   private_zone = false
# }
#
# # Create the DNS validation record
# resource "aws_route53_record" "cert_validation" {
#   for_each = {
#     for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
#       name   = dvo.resource_record_name
#       record = dvo.resource_record_value
#       type   = dvo.resource_record_type
#     }
#   }
#
#   allow_overwrite = true
#   name            = each.value.name
#   records         = [each.value.record]
#   ttl             = 60
#   type            = each.value.type
#   zone_id         = data.aws_route53_zone.main.zone_id
# }
#
# # Wait for validation to complete
# resource "aws_acm_certificate_validation" "main" {
#   certificate_arn         = aws_acm_certificate.main.arn
#   validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
# }
#
# # Map the dns record to the cloudfront distribution instead of IP
# # Then the cdn will check the location and the request
# # will be sent to the nearest IP and the files will be
# # served
# resource "aws_route53_record" "site_alias" {
#   zone_id = data.aws_route53_zone.main.zone_id
#   name    = var.domain_name
#
#   # Domain → IPv4 Address
#   type    = "A"
#
#   # Instead of pointing to an IP, point to an AWS service.
#   alias {
#     name                   = aws_cloudfront_distribution.static_site.domain_name
#     zone_id                = aws_cloudfront_distribution.static_site.hosted_zone_id
#     evaluate_target_health = false
#   }
# }