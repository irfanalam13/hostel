# Terraform + provider version pins and remote state (Phase 2, §7 IaC).
#
# Remote state uses S3 + DynamoDB locking, configured PARTIALLY here so the
# bucket/key/region are supplied per-environment at init time:
#   terraform init -backend-config=environments/backend-staging.hcl
# (Terraform Cloud is a drop-in alternative — replace the `backend "s3"` block
#  with a `cloud { organization = "..."; workspaces { tags = ["hostel"] } }`.)
terraform {
  required_version = ">= 1.9.0"

  backend "s3" {
    # Intentionally empty — values come from environments/backend-<env>.hcl.
    # Keys expected there: bucket, key, region, dynamodb_table, encrypt = true
  }

  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.3"
    }
    vercel = {
      source  = "vercel/vercel"
      version = "~> 3.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}
