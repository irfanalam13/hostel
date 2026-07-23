# Partial S3 backend config for production state.
#   terraform init -backend-config=environments/backend-production.hcl
bucket         = "REPLACE-hostel-tfstate"
key            = "production/terraform.tfstate"
region         = "ap-southeast-1"
dynamodb_table = "hostel-tf-locks"
encrypt        = true
