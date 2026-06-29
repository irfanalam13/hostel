# Automated TLS with Let's Encrypt

Issues and auto-renews the production certificate using certbot's **http-01
webroot** challenge — answered by the webroot nginx already serves on `:80`
(`/.well-known/acme-challenge/`). No DNS API, no Docker socket, no nginx
restart.

```
deploy/certbot/
  docker-compose.certbot.yml   adds the `certbot` service (compose profile "certbot")
  init-letsencrypt.sh          one-time first issuance (bootstraps a dummy cert)
  renew.sh                     idempotent renewal for cron
  deploy-hook.sh               copies a fresh cert into ./nginx/certs after issue/renew
```

## Prerequisites

- DNS `A`/`AAAA` for `${DOMAIN}` already points at the VPS.
- `deploy/.env` has `DOMAIN`, `CERTBOT_EMAIL`, and the rest of the prod values
  (copied from `.env.prod.example`).
- Ports 80 + 443 reach the host.

## First issuance (run once)

```bash
cd deploy
STAGING=1 ./certbot/init-letsencrypt.sh   # dry run against LE staging first
./certbot/init-letsencrypt.sh             # then the real cert
```

What it does:

1. Drops a throwaway self-signed cert so nginx can start (it can't boot without
   a cert, and certbot can't validate without nginx serving `:80` — this breaks
   the chicken-and-egg).
2. Brings up `web`, `frontend`, `nginx`.
3. Runs `certbot certonly --webroot`; on success the **deploy-hook** copies the
   real `fullchain.pem` + `privkey.pem` into `./nginx/certs`.
4. `nginx -s reload` picks them up with zero downtime.

> **Staging vs production:** LE production has strict rate limits (≈5 duplicate
> certs/week). Always validate the whole flow with `STAGING=1` first; staging
> certs are issued by an untrusted CA (browser will warn — that's expected).

## Automatic renewal

Certs last 90 days; certbot renews inside the last 30. Add a daily cron on the
VPS — `renew.sh` is a no-op until a cert is actually in its renewal window:

```cron
0 3 * * *  cd /home/USER/hostel/deploy && ./certbot/renew.sh >> /var/log/certbot-renew.log 2>&1
```

`renew.sh` runs `certbot renew` (same webroot + deploy-hook) then reloads nginx.
A graceful reload lets in-flight requests finish on the old workers — **zero
downtime renewal**.

### Alternative: containerised renewal loop (no host cron)

If you'd rather not use host cron, run a long-lived certbot that self-schedules
and let nginx self-reload on a timer. Add to the certbot service:

```yaml
    entrypoint: /bin/sh -c "trap exit TERM; while :; do certbot renew --webroot -w /var/www/certbot --deploy-hook /deploy-hook.sh; sleep 12h & wait $${!}; done"
```

and override nginx's command to reload every 6h:

```yaml
  nginx:
    command: /bin/sh -c "while :; do sleep 6h & wait $${!}; nginx -s reload; done & exec nginx -g 'daemon off;'"
```

The host-cron approach is recommended: it keeps `deploy.sh`'s nginx command
intact and is easier to observe/alert on.

## How it bridges to the existing manual flow

nginx still reads `./nginx/certs/{fullchain,privkey}.pem` exactly as documented
in [`../README.md`](../README.md). The only change is that those files are now
written **by the deploy-hook** instead of by hand. A Cloudflare Origin cert or a
commercial cert can still be dropped into the same path instead — see
[`docs/HTTPS.md`](../../docs/HTTPS.md) → *Certificate options*.

## Monitoring expiry

```bash
# Days until expiry of the live cert
echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null \
  | openssl x509 -noout -enddate
```

The repo's blackbox-exporter probe (`monitoring/`) can alert on
`probe_ssl_earliest_cert_expiry` — see `docs/HTTPS.md` → *Monitoring*.
