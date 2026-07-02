/**
 * Load test: dashboard + list reads (the hot read path).
 *
 * One login per VU, then a realistic browse loop hitting the dashboard summary
 * and the heaviest list endpoints. This surfaces N+1 queries and missing indexes
 * (Audit H6/H7) as p95 latency climbs with concurrency.
 */
import http from "k6/http";
import { check, sleep, group } from "k6";
import { api, scenario, thresholds, login } from "./lib/config.js";

export const options = {
  scenarios: scenario("read"),
  thresholds,
};

// The read endpoints below legitimately 404 on deploys where a module isn't
// enabled (the per-request check tolerates it). Treat 404 as an expected status
// too, so those reads don't inflate http_req_failed and trip its threshold.
http.setResponseCallback(http.expectedStatuses(200, 404));

export function setup() {
  // Nothing global; each VU logs in itself so cookie jars stay per-VU.
  return {};
}

export default function () {
  const headers = login(http);

  group("dashboard browse", () => {
    const endpoints = ["/dashboard/summary/", "/residents/", "/payments/", "/attendance/", "/complaints/"];
    for (const path of endpoints) {
      const res = http.get(api(path), { headers, tags: { name: path } });
      check(res, {
        [`${path} ok`]: (r) => r.status === 200 || r.status === 404, // 404 tolerated if endpoint differs per deploy
      });
    }
  });

  sleep(Math.random() * 2 + 1); // 1–3s think time
}
