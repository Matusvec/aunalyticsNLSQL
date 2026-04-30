import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

// Connect-src must include the backend so the browser can call /api/* directly.
// In production, prefer terminating both behind the same origin via a reverse proxy
// (see deploy/nginx.conf.example) — then "self" is sufficient.
const apiOrigin = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";

const connectSrc = ["'self'", apiOrigin].filter(Boolean).join(" ");

const csp = [
  "default-src 'self'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  // Next.js bootstraps with inline scripts; allow them only in prod where the runtime
  // signs them. In dev Next injects HMR which needs 'unsafe-eval'.
  isProd
    ? "script-src 'self' 'unsafe-inline'"
    : "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  `connect-src ${connectSrc}`,
  "form-action 'self'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
];

const nextConfig: NextConfig = {
  // Re-add `output: "standalone"` when deploying via systemd / Docker.
  poweredByHeader: false,
  reactStrictMode: true,
  compress: true,
  // Allow tunneled hosts to reach Next.js dev resources (HMR, etc.) when using `next dev`.
  // Production (`next start`) does not enforce this.
  allowedDevOrigins: [
    "*.trycloudflare.com",
    "localhost",
    "127.0.0.1",
    "149.28.120.74",
  ],
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
