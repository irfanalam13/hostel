# Deployment (single Ubuntu VPS + Docker Compose)

Roadmap Prompts 06 (staging) & 07 (production). Images are built and pushed to
GHCR by CI, then pulled and rolled out on the VPS by `deploy.sh` over SSH.

## Layout

```
deploy/
  docker-compose.prod.yml   registry-image stack + Nginx (TLS)
  nginx/templates/          app.conf.template (envsubst ${DOMAIN})
  nginx/certs/              fullchain.pem + privkey.pem (you provide)
  deploy.sh                 backup → migrate → health-gated swap → auto-rollback
  rollback.sh              revert to the previously deployed images
  .env.prod.example         copy to .env on the VPS
```

## One-time VPS setup

1. Install Docker + the compose plugin.
2. `mkdir -p ~/hostel/deploy` (this is `*_PATH` in the secrets below).
3. Copy `.env.prod.example` → `~/hostel/deploy/.env` and fill in real values.
   `.env` is **never** shipped by CI, so your secrets persist across deploys.
4. Put TLS certs at `nginx/certs/fullchain.pem` and `privkey.pem` (e.g. certbot:
   `certbot certonly --standalone -d app.yourdomain.com`, then symlink/copy).
5. First deploy can be run manually:
   `GHCR_USER=… GHCR_TOKEN=… ./deploy.sh ghcr.io/owner/hostel-backend:vX ghcr.io/owner/hostel-frontend:vX`

## CI/CD secrets & variables

Per environment (`STAGING_*` / `PROD_*`) **secrets**:
`*_SSH_HOST`, `*_SSH_USER`, `*_SSH_KEY`, `*_SSH_PORT` (opt), `*_PATH`,
plus `GHCR_USERNAME`, `GHCR_TOKEN` (read:packages), and optional `SLACK_WEBHOOK_URL`.

**Variables**: `STAGING_URL`, `STAGING_API_BASE_URL`, `PROD_URL`,
`PROD_API_BASE_URL`, and `SLACK_WEBHOOK_CONFIGURED` (`true` to enable Slack).

## How a deploy works

1. **Build** images → GHCR, tagged with the release/sha (`build-images.yml`).
2. **Ship** `deploy/` to the VPS via SCP (your `.env` is untouched).
3. `deploy.sh`: records current images → logs in to GHCR → pulls new images →
   `pg_dump` safety backup → reviews + applies migrations → `compose up --wait`
   (health-gated) → verifies `/health/*`. **Any failure after the swap triggers
   an automatic rollback** to the previous images.
4. **Smoke / health verification** against the public URL.
5. **Deployment record** created via the GitHub Deployments API (history).

## Notes

- Rollout is **health-gated, near-zero-downtime** (Nginx fronts the app; the new
  container must pass its healthcheck before traffic shifts). For strict
  zero-downtime add a second `web` replica and an Nginx upstream with two
  members, recreated one at a time.
- **Migration safety**: a `pg_dump` is taken before migrating, and the plan is
  printed. For backward-incompatible changes use expand/contract (deploy additive
  migration → deploy code → later remove old columns) so rollback stays safe.
- Rollback manually any time: `./rollback.sh`.
