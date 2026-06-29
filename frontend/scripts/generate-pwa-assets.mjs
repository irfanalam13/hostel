/**
 * generate-pwa-assets.mjs
 *
 * Generates every raster asset the PWA needs from a single inline SVG source,
 * so the brand can be re-rendered deterministically (no binary blobs checked in
 * that nobody can regenerate). Run with:  node scripts/generate-pwa-assets.mjs
 *
 * Outputs (under public/):
 *   icons/icon-192.png            maskable:false  transparent-safe square icon
 *   icons/icon-512.png            high-res app icon (store / splash)
 *   icons/icon-maskable-192.png   adaptive icon with safe-zone padding
 *   icons/icon-maskable-512.png   adaptive icon with safe-zone padding
 *   icons/apple-touch-icon.png    180x180, opaque background (iOS)
 *   icons/favicon-16.png / -32.png / -48.png
 *   icons/shortcut-*.png          96x96 launcher-shortcut glyphs
 *   screenshots/wide.png          1280x720  (form_factor: wide)
 *   screenshots/narrow.png        720x1280  (form_factor: narrow)
 *
 * Brand tokens are kept in sync with src/app/globals.css (--accent #2563eb).
 */
import sharp from "sharp";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PUBLIC = resolve(ROOT, "public");

const ACCENT = "#2563eb";
const ACCENT_DARK = "#1d4ed8";
const INK = "#0f172a";
const PAPER = "#f8fafc";

/** The hostel mark: a building with a bed-arch doorway, on a brand gradient. */
function logoSvg({ size = 512, padding = 0.0, bg = true } = {}) {
  const s = size;
  const inset = s * padding; // safe-zone padding for maskable icons
  const inner = s - inset * 2;
  // glyph drawn in a 0..100 viewBox, then scaled into the inner area
  const glyph = `
    <g transform="translate(${inset},${inset}) scale(${inner / 100})">
      <!-- roof -->
      <path d="M50 18 L82 40 L18 40 Z" fill="#ffffff"/>
      <!-- body -->
      <rect x="24" y="40" width="52" height="42" rx="4" fill="#ffffff"/>
      <!-- door / bed arch -->
      <path d="M42 82 L42 62 Q50 54 58 62 L58 82 Z" fill="${ACCENT}"/>
      <!-- windows -->
      <rect x="30" y="48" width="9" height="9" rx="1.5" fill="${ACCENT}"/>
      <rect x="61" y="48" width="9" height="9" rx="1.5" fill="${ACCENT}"/>
    </g>`;
  const background = bg
    ? `<defs>
         <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
           <stop offset="0" stop-color="${ACCENT}"/>
           <stop offset="1" stop-color="${ACCENT_DARK}"/>
         </linearGradient>
       </defs>
       <rect width="${s}" height="${s}" rx="${s * 0.22}" fill="url(#g)"/>`
    : "";
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}">${background}${glyph}</svg>`;
}

function shortcutSvg(label) {
  // simple lettermark tile for launcher shortcuts
  return `<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">
    <rect width="96" height="96" rx="22" fill="${ACCENT}"/>
    <text x="48" y="62" font-family="Segoe UI, Arial, sans-serif" font-size="44"
          font-weight="700" fill="#fff" text-anchor="middle">${label}</text>
  </svg>`;
}

function screenshotSvg(w, h) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    <rect width="${w}" height="${h}" fill="${PAPER}"/>
    <rect x="0" y="0" width="${w}" height="${Math.round(h * 0.12)}" fill="${ACCENT}"/>
    <text x="${Math.round(w * 0.05)}" y="${Math.round(h * 0.08)}" font-family="Segoe UI, Arial, sans-serif"
          font-size="${Math.round(h * 0.045)}" font-weight="700" fill="#fff">Hostel Management System</text>
    <g fill="#fff" stroke="#e2e8f0">
      ${[0, 1, 2].map((i) => {
        const cw = Math.round((w - 80) / 3);
        const x = 30 + i * (cw + 10);
        const y = Math.round(h * 0.16);
        return `<rect x="${x}" y="${y}" width="${cw}" height="${Math.round(h * 0.18)}" rx="14"/>`;
      }).join("")}
      <rect x="30" y="${Math.round(h * 0.4)}" width="${w - 60}" height="${Math.round(h * 0.5)}" rx="14"/>
    </g>
    <text x="${Math.round(w * 0.05)}" y="${Math.round(h * 0.27)}" font-family="Segoe UI, Arial, sans-serif"
          font-size="${Math.round(h * 0.03)}" font-weight="600" fill="${INK}">Residents · Billing · Occupancy</text>
  </svg>`;
}

async function out(rel, buf) {
  const p = resolve(PUBLIC, rel);
  await mkdir(dirname(p), { recursive: true });
  await writeFile(p, buf);
  console.log("  ✓", rel);
}

const png = (svg, size, opts = {}) =>
  sharp(Buffer.from(svg)).resize(size, size, opts).png().toBuffer();

async function main() {
  console.log("Generating PWA assets…");

  // Standard (transparent-safe) icons
  await out("icons/icon-192.png", await png(logoSvg({ size: 192 }), 192));
  await out("icons/icon-512.png", await png(logoSvg({ size: 512 }), 512));

  // Maskable icons: glyph inside the ~80% safe zone, full-bleed gradient bg
  await out("icons/icon-maskable-192.png", await png(logoSvg({ size: 192, padding: 0.14 }), 192));
  await out("icons/icon-maskable-512.png", await png(logoSvg({ size: 512, padding: 0.14 }), 512));

  // Apple touch icon — opaque (iOS ignores transparency / rounds corners itself)
  await out(
    "icons/apple-touch-icon.png",
    await sharp(Buffer.from(logoSvg({ size: 180 })))
      .resize(180, 180)
      .flatten({ background: ACCENT })
      .png()
      .toBuffer(),
  );

  // Favicons
  for (const sz of [16, 32, 48]) {
    await out(`icons/favicon-${sz}.png`, await png(logoSvg({ size: sz }), sz));
  }

  // Launcher-shortcut glyphs
  await out("icons/shortcut-dashboard.png", await png(shortcutSvg("D"), 96));
  await out("icons/shortcut-residents.png", await png(shortcutSvg("R"), 96));
  await out("icons/shortcut-payments.png", await png(shortcutSvg("P"), 96));

  // Screenshots
  await out("screenshots/wide.png", await sharp(Buffer.from(screenshotSvg(1280, 720))).png().toBuffer());
  await out("screenshots/narrow.png", await sharp(Buffer.from(screenshotSvg(720, 1280))).png().toBuffer());

  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
