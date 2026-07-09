terraform {
  backend "s3" {
    bucket       = "varun-devops-s3-2026"
    key          = "tasmanian_grid_platform/terraform.tfstate"
    region       = "ap-southeast-2"
    use_lockfile = "true"
    encrypt      = true
  }
}
