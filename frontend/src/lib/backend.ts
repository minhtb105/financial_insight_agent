/**
 * Central backend URL helper — single source of truth.
 * Prevents duplication of `process.env.API_URL || ... || "http://localhost:8000"` across 4+ files.
 */

export function getBackendUrl(): string {
  const raw = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  return raw.replace(/\/$/, "")
}

export async function fetchBackend(path: string, init?: RequestInit): Promise<Response> {
  const base = getBackendUrl()
  const url = `${base}${path.startsWith("/") ? "" : "/"}${path}`
  return fetch(url, { cache: "no-store", ...(init || {}) })
}

export function backendUrl(path: string): string {
  return `${getBackendUrl()}${path.startsWith("/") ? "" : "/"}${path}`
}
