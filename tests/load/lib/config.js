/**
 * Shared k6 configuration + helpers for the load suite.
 *
 * Every script picks a scenario profile via the SCENARIO env var:
 *   smoke  — 1 VU, 30s          (does the endpoint work under k6 at all?)
 *   load   — ramp to 50 VUs     (expected production traffic)
 *   stress — ramp to 300 VUs    (find the breaking point)
 *   spike  — 0→400→0 fast       (sudden surge resilience)
 *   soak   — 30 VUs for 30m     (memory leaks / connection exhaustion)
 *
 * Targets are env-driven so the same scripts run against local, staging or a
 * throwaway perf environment — NEVER point these at production.
 */
import { check } from "k6";

export const BASE_URL = (__ENV.BASE_URL || "http://localhost:8000").replace(/\/+$/, "");
export const HOSTEL_ID = __ENV.HOSTEL_ID || "HTL-ABC12345";
export const USERNAME = __ENV.USERNAME || "warden";
export const PASSWORD = __ENV.PASSWORD || "TestPass!234";

const PROFILES = {
  smoke: {
    executor: "constant-vus",
    vus: 1,
    duration: "30s",
  },
  load: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "1m", target: 50 },
      { duration: "3m", target: 50 },
      { duration: "1m", target: 0 },
    ],
  },
  stress: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "2m", target: 100 },
      { duration: "3m", target: 300 },
      { duration: "2m", target: 0 },
    ],
  },
  spike: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "10s", target: 400 },
      { duration: "30s", target: 400 },
      { duration: "10s", target: 0 },
    ],
  },
  soak: {
    executor: "constant-vus",
    vus: 30,
    duration: "30m",
  },
};

export function scenario(name = "main") {
  const profile = PROFILES[__ENV.SCENARIO || "smoke"];
  if (!profile) throw new Error(`Unknown SCENARIO "${__ENV.SCENARIO}"`);
  return { [name]: profile };
}

// Global SLOs — a run fails (non-zero exit) if any threshold is breached, so CI
// can gate on performance regressions, not just correctness.
export const thresholds = {
  http_req_failed: ["rate<0.01"], // <1% errors
  http_req_duration: ["p(95)<800", "p(99)<2000"], // 95% < 800ms, 99% < 2s
  checks: ["rate>0.99"],
};

export function api(path) {
  return `${BASE_URL}/api${path.startsWith("/") ? path : `/${path}`}`;
}

/**
 * Authenticate a VU. Returns the headers (CSRF + hostel) to reuse; the session
 * cookies ride in k6's per-VU cookie jar automatically.
 */
export function login(http) {
  // Prime CSRF.
  const csrfRes = http.get(api("/auth/csrf/"));
  let csrf = "";
  try {
    csrf = csrfRes.json("csrftoken") || "";
  } catch (_) {
    /* some deployments return the token only as a cookie */
  }

  const res = http.post(
    api("/auth/login/"),
    JSON.stringify({ hostel_id: HOSTEL_ID, username: USERNAME, password: PASSWORD }),
    { headers: { "Content-Type": "application/json", "X-Hostel-Code": HOSTEL_ID }, tags: { name: "login" } }
  );
  check(res, { "login 200": (r) => r.status === 200 });

  return {
    "Content-Type": "application/json",
    "X-Hostel-Code": HOSTEL_ID,
    ...(csrf ? { "X-CSRFToken": csrf } : {}),
  };
}
