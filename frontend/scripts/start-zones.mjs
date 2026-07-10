/**
 * Start BOTH production zone servers for e2e/lighthouse/cypress runs:
 *   - admin zone  → :3101 (override: ZONE_ADMIN_PORT)
 *   - client zone → :3100 (override: ZONE_CLIENT_PORT), proxying non-marketing
 *     paths to the admin zone via ADMIN_ZONE_URL.
 *
 * Both apps must already be built (`npm run build`). Prints ALL_ZONES_READY
 * once both servers answer — test runners key their ready-check on that line
 * (or on the client URL itself). Exits non-zero if either server dies.
 */
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const CLIENT_PORT = Number(process.env.ZONE_CLIENT_PORT || process.env.LHCI_PORT || 3100);
const ADMIN_PORT = Number(process.env.ZONE_ADMIN_PORT || 3101);

const npx = process.platform === "win32" ? "npx.cmd" : "npx";

let shuttingDown = false;

function start(name, appDir, port, extraEnv = {}) {
  const child = spawn(npx, ["next", "start", "--port", String(port)], {
    cwd: path.join(root, "apps", appDir),
    env: { ...process.env, ...extraEnv },
    stdio: ["ignore", "pipe", "pipe"],
    shell: process.platform === "win32",
  });
  child.stdout.on("data", (d) => process.stdout.write(`[${name}] ${d}`));
  child.stderr.on("data", (d) => process.stderr.write(`[${name}] ${d}`));
  child.on("exit", (code) => {
    if (shuttingDown) return;
    console.error(`[start-zones] ${name} exited with code ${code}`);
    process.exit(code ?? 1);
  });
  return child;
}

async function waitFor(url, timeoutMs = 120_000) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    try {
      const res = await fetch(url, { redirect: "manual" });
      if (res.status < 500) return;
    } catch {
      /* not up yet */
    }
    if (Date.now() > deadline) throw new Error(`timed out waiting for ${url}`);
    await new Promise((r) => setTimeout(r, 500));
  }
}

const children = [
  start("admin", "admin", ADMIN_PORT),
  start("client", "client", CLIENT_PORT, {
    ADMIN_ZONE_URL: process.env.ADMIN_ZONE_URL || `http://localhost:${ADMIN_PORT}`,
  }),
];

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => {
    shuttingDown = true;
    for (const c of children) c.kill();
    process.exit(0);
  });
}

await waitFor(`http://localhost:${ADMIN_PORT}/login`);
await waitFor(`http://localhost:${CLIENT_PORT}/`);
console.log("ALL_ZONES_READY");
