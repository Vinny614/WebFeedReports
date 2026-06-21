import { NextRequest } from "next/server";

// Backend-for-Frontend proxy. The browser calls same-origin "/api/*" and this
// handler forwards to the API service using the runtime API_BASE_URL injected
// by the Container App. This keeps the API URL out of the client bundle and
// lets the API stay internal-only (no public ingress required).
export const dynamic = "force-dynamic";

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const base = process.env.API_BASE_URL ?? "http://localhost:8000";
  const target = `${base}/${path.join("/")}${req.nextUrl.search}`;

  const init: RequestInit = {
    method: req.method,
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }

  const res = await fetch(target, init);
  const body = await res.text();
  return new Response(body, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("content-type") ?? "application/json",
    },
  });
}

export function GET(req: NextRequest, ctx: { params: { path: string[] } }): Promise<Response> {
  return proxy(req, ctx.params.path);
}

export function POST(req: NextRequest, ctx: { params: { path: string[] } }): Promise<Response> {
  return proxy(req, ctx.params.path);
}
