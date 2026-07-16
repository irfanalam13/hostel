# =============================================================================
# Render — backend (Django/Gunicorn), Celery worker, ML service, Postgres, Redis
# =============================================================================
# ⚠️  RECONCILE BEFORE FIRST APPLY: attribute names below follow the
#     render-oss/render provider (~> 1.3). Confirm against the version you pin
#     (`terraform providers schema -json`) and ADOPT the already-running
#     dashboard services with `terraform import` (see README) so the first apply
#     is a no-op, NOT a recreate. Never let Terraform recreate the database.

locals {
  # Env vars common to backend + worker (non-secret; secrets are separate).
  backend_env = {
    DJANGO_SETTINGS_MODULE = { value = "config.settings" }
    DEBUG                  = { value = "False" }
    DJANGO_SECRET_KEY      = { value = var.django_secret_key }
    ML_SHARED_SECRET       = { value = var.ml_shared_secret }
    DATABASE_URL           = { value = render_postgres.db.connection_info.internal_connection_string }
    REDIS_URL              = { value = render_redis.cache.connection_info.internal_connection_string }
    CELERY_BROKER_URL      = { value = render_redis.cache.connection_info.internal_connection_string }
  }
}

resource "render_postgres" "db" {
  name          = "hostel-db-${var.environment}"
  plan          = var.environment == "production" ? "standard" : "basic_256mb"
  region        = var.render_region
  version       = "16"
  database_name = "hostel"
  database_user = "hostel"
}

resource "render_redis" "cache" {
  name              = "hostel-redis-${var.environment}"
  plan              = "starter"
  region            = var.render_region
  max_memory_policy = "noeviction" # broker must not silently drop queued tasks
}

resource "render_web_service" "backend" {
  name   = "hostel-backend-${var.environment}"
  plan   = var.render_plan
  region = var.render_region

  runtime_source = {
    docker = {
      repo_url        = var.repo_url
      branch          = var.git_branch
      dockerfile_path = "./backend/Dockerfile"
      context         = "./backend"
    }
  }

  health_check_path = "/health/"
  # auto-deploy (CD gate: var.render_auto_deploy — false in prod, true in staging)
  # is configured post-reconciliation; the render provider exposes it under a
  # different key than a bare `auto_deploy`. See README + docs/CD_STRATEGY.md.
  env_vars = local.backend_env
}

resource "render_background_worker" "celery" {
  name   = "hostel-celery-${var.environment}"
  plan   = var.render_plan
  region = var.render_region

  runtime_source = {
    docker = {
      repo_url        = var.repo_url
      branch          = var.git_branch
      dockerfile_path = "./backend/Dockerfile"
      context         = "./backend"
    }
  }

  start_command = "celery -A config worker -l info"
  # auto-deploy configured post-reconciliation (see README).
  env_vars = local.backend_env
}

resource "render_web_service" "ml" {
  name   = "hostel-ml-${var.environment}"
  plan   = var.render_plan
  region = var.render_region

  runtime_source = {
    docker = {
      repo_url        = var.repo_url
      branch          = var.git_branch
      dockerfile_path = "./ML_hostel/Dockerfile"
      context         = "./ML_hostel"
    }
  }

  health_check_path = "/health/"
  # auto-deploy configured post-reconciliation (see README).
  env_vars = {
    ML_PROVIDER       = { value = "gemini" }
    ML_MODEL          = { value = "gemini-flash-latest" }
    ML_DJANGO_API_URL = { value = var.api_base_url }
    # ML_SHARED_SECRET MUST equal the backend's — keep them in lockstep.
    ML_SHARED_SECRET = { value = var.ml_shared_secret }
    # Provider API key is set out-of-band in the dashboard (sync:false) or via a
    # separate secret var; not stored in plaintext state here.
  }
}
