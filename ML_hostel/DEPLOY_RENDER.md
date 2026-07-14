# Deploying ML_hostel to Render

`ML_hostel` is a FastAPI service — it must run as a **container / persistent
process**, not on Vercel (Vercel can't run the Dockerfile, and it 404s because it
finds nothing to serve). Host it on **Render**, next to your Django backend.

The cloud deployment uses **Google Gemini** (via its OpenAI-compatibility layer)
instead of Ollama — Ollama can't run on Render's CPU instances. The code is
provider-agnostic; this is pure config.

> ⚠️ **Rotate your Gemini API key.** It was shared in plain text — generate a new
> one at https://aistudio.google.com/apikey and use that below. Never commit it.

---

## 1. Create the ML service on Render

Dashboard → **New → Web Service** → connect this repo, then:

| Field | Value |
|---|---|
| Name | `hostel-ml` (any) |
| Language / Runtime | **Docker** |
| Root Directory | `ML_hostel` |
| Dockerfile Path | `Dockerfile` (relative to root dir) |
| Branch | `main` (after the PR merges) |
| Health Check Path | `/health/` |
| Instance Type | `Starter` (Free sleeps → cold-start 404s until it wakes) |

Render injects `$PORT`; the Dockerfile already binds it.

### Environment variables (ML service)

| Key | Value | Secret? |
|---|---|---|
| `ML_PROVIDER` | `gemini` | no |
| `ML_MODEL` | `gemini-flash-latest` | no |
| `ML_EMBED_MODEL` | `gemini-embedding-001` | no |
| `ML_DJANGO_API_URL` | `https://hostel-mwre.onrender.com/api` (your backend) | no |
| `ML_GEMINI_API_KEY` | your (rotated) Gemini key | **yes** |
| `ML_SHARED_SECRET` | a long random string — **must equal the backend's** | **yes** |
| `ML_ALLOWED_ORIGINS` | your admin app origin, e.g. `https://your-admin.vercel.app` | **yes** |

Generate a shared secret: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

After deploy, verify: `curl https://hostel-ml.onrender.com/health/` → `{"status":"ok",...}`
and `curl https://hostel-ml.onrender.com/health/provider/`.

---

## 2. Add matching env vars to the **backend** (existing Render service)

The backend mints the context token and the browser needs the ML stream URL.

| Key | Value |
|---|---|
| `ML_SHARED_SECRET` | **same value** as the ML service |
| `ML_SERVICE_URL` | `https://hostel-ml.onrender.com` (used by ingestion) |
| `ML_PUBLIC_URL` | `https://hostel-ml.onrender.com` (browser SSE stream base) |

(Trigger a redeploy so they take effect.)

---

## 3. Add one env var to the **admin frontend** (Vercel)

The admin app opens the assistant's SSE stream directly against the ML origin, so
that origin must be allowed by the strict CSP.

| Key | Value |
|---|---|
| `NEXT_PUBLIC_ML_BASE_URL` | `https://hostel-ml.onrender.com` |

Redeploy the admin Vercel project. (Must match the backend's `ML_PUBLIC_URL`.)

---

## 4. Delete the broken Vercel deployment

Remove the `hostel-mufv-self` Vercel project — it can never serve this service.

---

## How the pieces talk (prod)

```
Browser (admin, Vercel)
  ├─ POST https://hostel-mwre.onrender.com/api/ai/chat/   (cookie) → context token + stream_url
  └─ SSE  https://hostel-ml.onrender.com/v1/chat/stream   (Bearer token; CORS + CSP allow it)
                     │
             hostel-ml (Render, this service) ── Gemini API (chat + embeddings)
                     └─ tool calls → https://hostel-mwre.onrender.com/api/ai/tools/…  (Bearer token)
```

Tenancy + RBAC stay enforced by Django on every hop; the ML service holds no data
and no DB credentials. Switching provider later (OpenAI, Groq, self-hosted Ollama
on a GPU box) is just `ML_PROVIDER` + keys — no code change.
