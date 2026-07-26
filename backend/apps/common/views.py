"""Root status / landing page.

A plain Django view (no DRF envelope/auth) served at ``/`` so hitting the API
host in a browser shows a useful "backend is running" dashboard instead of a
404. It links to the Swagger UI / ReDoc / schema and live-checks the health
endpoints from the browser.
"""
import django
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>My Hostel API</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         background:#0b1220; color:#e6edf6; min-height:100vh; }}
  .wrap {{ max-width: 880px; margin: 0 auto; padding: 48px 20px 64px; }}
  .badge {{ display:inline-flex; align-items:center; gap:8px; background:#0f2a1a; color:#5ef0a0;
            border:1px solid #1f6b43; padding:6px 14px; border-radius:999px; font-weight:600; font-size:14px; }}
  .dot {{ width:9px; height:9px; border-radius:50%; background:#5ef0a0; box-shadow:0 0 0 4px rgba(94,240,160,.15); }}
  h1 {{ font-size: 30px; margin: 18px 0 6px; }}
  p.sub {{ color:#9fb0c7; margin:0 0 28px; }}
  .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr)); gap:14px; }}
  a.card {{ display:block; text-decoration:none; color:inherit; background:#111c2e; border:1px solid #1e2c44;
            border-radius:14px; padding:18px; transition:.15s; }}
  a.card:hover {{ border-color:#3b82f6; transform:translateY(-2px); }}
  a.card .t {{ font-weight:700; font-size:16px; }}
  a.card .d {{ color:#9fb0c7; font-size:13px; margin-top:4px; }}
  section {{ margin-top:34px; }}
  h2 {{ font-size:14px; text-transform:uppercase; letter-spacing:.08em; color:#9fb0c7; margin:0 0 12px; }}
  .health {{ display:flex; flex-direction:column; gap:8px; }}
  .hrow {{ display:flex; align-items:center; gap:10px; background:#0f1929; border:1px solid #1e2c44;
           border-radius:10px; padding:10px 14px; font-size:14px; }}
  .hdot {{ width:10px; height:10px; border-radius:50%; background:#54607a; flex:none; }}
  .hdot.ok {{ background:#5ef0a0; }} .hdot.bad {{ background:#ff6b6b; }} .hdot.warn {{ background:#f5b54a; }}
  .hrow .tag {{ font-size:10px; text-transform:uppercase; letter-spacing:.05em; color:#6b7a93;
               border:1px solid #2a3a55; border-radius:6px; padding:1px 6px; }}
  .hrow .name {{ font-weight:600; }} .hrow .path {{ color:#6b7a93; font-family: ui-monospace, monospace; font-size:12px; }}
  .hrow .stat {{ margin-left:auto; color:#9fb0c7; font-size:12px; }}
  footer {{ margin-top:40px; color:#6b7a93; font-size:12px; border-top:1px solid #1e2c44; padding-top:16px; }}
  code {{ background:#0f1929; padding:2px 6px; border-radius:6px; }}
</style>
</head>
<body>
  <div class="wrap">
    <span class="badge"><span class="dot"></span> Backend is running</span>
    <h1>My Hostel API</h1>
    <p class="sub">Django {django_version} · {debug_label} · {now}</p>

    <div class="grid">
      <a class="card" href="/api/docs/"><div class="t">📘 Swagger UI</div><div class="d">Interactive API explorer — try every endpoint</div></a>
      <a class="card" href="/api/redoc/"><div class="t">📕 ReDoc</div><div class="d">Clean, readable API reference</div></a>
      <a class="card" href="/api/schema/"><div class="t">🧬 OpenAPI Schema</div><div class="d">Raw schema (YAML) for codegen/tools</div></a>
      <a class="card" href="/admin/"><div class="t">⚙️ Django Admin</div><div class="d">Staff back-office</div></a>
    </div>

    <section>
      <h2>Live health</h2>
      <div class="health" id="health">
        <div class="hrow" data-url="/health/"><span class="hdot"></span><span class="name">Liveness</span><span class="path">/health/</span><span class="stat">checking…</span></div>
        <div class="hrow" data-url="/health/database/"><span class="hdot"></span><span class="name">Database</span><span class="path">/health/database/</span><span class="stat">checking…</span></div>
        <div class="hrow" data-url="/health/cache/" data-optional="1"><span class="hdot"></span><span class="name">Cache (Redis)</span><span class="tag">optional</span><span class="path">/health/cache/</span><span class="stat">checking…</span></div>
        <div class="hrow" data-url="/health/celery/" data-optional="1"><span class="hdot"></span><span class="name">Celery workers</span><span class="tag">optional</span><span class="path">/health/celery/</span><span class="stat">checking…</span></div>
      </div>
    </section>

    <footer>This page is served only as a status/landing page. The application UI is the separate Next.js frontend.</footer>
  </div>

  <script>
    document.querySelectorAll('#health .hrow').forEach(async (row) => {{
      const dot = row.querySelector('.hdot');
      const stat = row.querySelector('.stat');
      const optional = row.dataset.optional === '1';
      try {{
        const res = await fetch(row.dataset.url, {{ cache: 'no-store' }});
        const ok = res.ok;
        // Optional dev dependencies (cache/celery) show amber "not running"
        // rather than a red error when they're simply not up locally.
        dot.classList.add(ok ? 'ok' : (optional ? 'warn' : 'bad'));
        stat.textContent = ok
          ? ('healthy · ' + res.status)
          : (optional ? 'not running · ' + res.status : 'down · ' + res.status);
      }} catch (e) {{
        dot.classList.add(optional ? 'warn' : 'bad');
        stat.textContent = optional ? 'not running' : 'unreachable';
      }}
    }});
  </script>
</body>
</html>"""


@require_GET
def index(request):
    html = _PAGE.format(
        django_version=django.get_version(),
        debug_label="DEBUG" if settings.DEBUG else "production",
        now=timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z"),
    )
    resp = HttpResponse(html)
    # This page intentionally uses inline CSS/JS; relax the strict API CSP for
    # just this response (the middleware uses setdefault, so this wins).
    resp["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
    return resp
