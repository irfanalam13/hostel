/**
 * Load test: concurrent payment writes (the write + locking path).
 *
 * Payments go through allocate_payment(), which locks the fee ledger
 * (select_for_update) — the place most likely to serialise or deadlock under
 * concurrency. Each request carries a unique Idempotency-Key so the backend's
 * IdempotencyMiddleware is exercised exactly as the offline-sync replay would.
 *
 * NOTE: this mutates data — run only against a disposable perf environment.
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";
import { api, scenario, thresholds, login } from "./lib/config.js";

export const options = {
  scenarios: scenario("write"),
  thresholds: {
    ...thresholds,
    // Writes are heavier; relax p95 a little vs reads.
    http_req_duration: ["p(95)<1200", "p(99)<3000"],
  },
};

export default function () {
  const headers = login(http);

  const body = JSON.stringify({ amount: 100, method: "cash", note: "k6 load test" });
  const res = http.post(api("/payments/"), body, {
    headers: { ...headers, "Idempotency-Key": uuidv4() },
    tags: { name: "create-payment" },
  });

  check(res, {
    "created or validation": (r) => [201, 400, 409].includes(r.status),
    "not a 5xx (no deadlock/500)": (r) => r.status < 500,
  });

  sleep(1);
}
