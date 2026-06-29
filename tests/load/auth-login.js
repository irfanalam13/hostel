/**
 * Load test: authentication throughput.
 *
 * The login path is the most security-sensitive and CPU-heavy endpoint (password
 * hashing + JWT issuance), so it's the first thing to fall over under load. This
 * measures how many logins/sec the stack sustains within the latency SLO.
 *
 *   k6 run tests/load/auth-login.js                 # smoke
 *   SCENARIO=stress BASE_URL=https://staging k6 run tests/load/auth-login.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { api, scenario, thresholds, HOSTEL_ID, USERNAME, PASSWORD } from "./lib/config.js";

export const options = {
  scenarios: scenario("auth"),
  thresholds: {
    ...thresholds,
    "http_req_duration{name:login}": ["p(95)<1500"], // hashing is intentionally slow
  },
};

export default function () {
  http.get(api("/auth/csrf/"));
  const res = http.post(
    api("/auth/login/"),
    JSON.stringify({ hostel_id: HOSTEL_ID, username: USERNAME, password: PASSWORD }),
    { headers: { "Content-Type": "application/json", "X-Hostel-Code": HOSTEL_ID }, tags: { name: "login" } }
  );
  check(res, {
    "status is 200": (r) => r.status === 200,
    "sets a session": (r) => r.status === 200 && /sessionid|access|refresh/i.test(r.headers["Set-Cookie"] || ""),
  });
  sleep(1);
}
