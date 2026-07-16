# Handy references after apply. URLs help wire cross-service env + smoke checks.

output "backend_url" {
  description = "Public URL of the Django backend service."
  value       = render_web_service.backend.url
}

output "ml_url" {
  description = "Public URL of the ML/AI service."
  value       = render_web_service.ml.url
}

output "vercel_client_project_id" {
  value = vercel_project.client.id
}

output "vercel_admin_project_id" {
  value = vercel_project.admin.id
}

output "environment" {
  value = var.environment
}
