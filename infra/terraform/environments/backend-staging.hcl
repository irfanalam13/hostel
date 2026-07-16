# Partial S3 backend config for staging state.
#   terraform init -backend-config=environments/backend-staging.hcl
bucket         = "REPLACE-hostel-tfstate"
key            = "staging/terraform.tfstate"
region         = "ap-southeast-1"
dynamodb_table = "hostel-tf-locks"
encrypt        = true
