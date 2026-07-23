// =============================================================================
// k6 load test — edge security foundation (Prompt 07).
//
// Verifies the layered rate limiting behaves correctly under load:
//   * flood scenario: a single source hammering the API must be throttled
//     (429 with Retry-After), and the app must stay healthy while it happens.
//   * legit scenario: a normal browsing rate must see (almost) no 429s and
//     keep p95 latency within budget while the flood is running.
//
// Run against the dev gateway (or staging — NEVER production):
//   k6 run deploy/load/k6-rate-limit.js
//   k6 run -e BASE_URL=https://staging.example.com deploy/load/k6-rate-limit.js
//
// NOTE: in development the security layer defaults to monitor mode / generous
// limits. To exercise enforcement locally set SECURITY_ENVIRONMENT=production
// (or SECURITY_MODE=enforce and tight SECURITY_RATE_IP_* values) on the web
// service and restart, or use a SecuritySetting row (hot reload, no restart).
// =============================================================================
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost";

const floodThrottled = new Rate("flood_throttled");     // fraction of flood 429s
const legitThrottled = new Rate("legit_throttled");     // must stay ~0
const legitLatency = new Trend("legit_latency", true);

export const options = {
  scenarios: {
    flood: {
      executor: "constant-arrival-rate",
      rate: 100, timeUnit: "1s",           // 100 req/s from the flood source
      duration: "60s",
      preAllocatedVUs: 50, maxVUs: 200,
      exec: "flood",
    },
    legit: {
      executor: "constant-vus",
      vus: 5, duration: "60s",             // 5 humans browsing politely
      exec: "legit",
    },
  },
  thresholds: {
    // The flood must actually be throttled once app limits are exceeded.
    flood_throttled: ["rate>0.2"],
    // Legitimate users must be unaffected by someone else's flood.
    legit_throttled: ["rate<0.01"],
    legit_latency: ["p(95)<500"],
    // The app never 5xxs under pressure (429 is the correct answer, not 500).
    http_req_failed: ["rate<0.01"],
  },
};

export function flood() {
  const res = http.get(`${BASE_URL}/api/health/`, {
    headers: { "User-Agent": "k6-flood-scenario" },
    tags: { scenario: "flood" },
  });
  floodThrottled.add(res.status === 429);
  check(res, {
    "flood: 2xx or 429 (never 5xx)": (r) => r.status < 500,
    "flood: 429 carries Retry-After": (r) =>
      r.status !== 429 || r.headers["Retry-After"] !== undefined,
  });
}

export function legit() {
  const res = http.get(`${BASE_URL}/`, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126",
    },
    tags: { scenario: "legit" },
  });
  legitThrottled.add(res.status === 429);
  legitLatency.add(res.timings.duration);
  check(res, { "legit: 200": (r) => r.status === 200 });
  sleep(1 + Math.random());                // human-ish pacing
}
