/**
 * Deployment settings, fixed at build time by Vite environment variables.
 *
 * - Local development and the Docker image: the API is on the same origin and
 *   the app is served from "/", so both values stay empty / "/".
 * - GitHub Pages: built with VITE_BASE=/BTLXLA/ and VITE_API_BASE pointing at
 *   the Render service, e.g. https://btlxla.onrender.com.
 */
export const API_BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? "").replace(/\/+$/, "");

/** True when the interface talks to a server on another origin (e.g. Render). */
export const REMOTE_API = API_BASE !== "";

/** Absolute URL for an API path such as "/api/analyze". */
export function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}

/** URL of a file in frontend/public, respecting Vite's base path. */
export function assetUrl(path: string) {
  return `${import.meta.env.BASE_URL}${path.replace(/^\/+/, "")}`;
}

/** Router base without the trailing slash ("" at the site root). */
export const ROUTER_BASENAME = import.meta.env.BASE_URL.replace(/\/+$/, "");

/**
 * The API returns root-relative result URLs ("/results/<job>/…"). When the API
 * is on another origin, prefix every such string so images and downloads load
 * from the server rather than from GitHub Pages.
 */
export function withApiBase<T>(value: T): T {
  if (!REMOTE_API) return value;
  if (typeof value === "string") return (value.startsWith("/results/") ? `${API_BASE}${value}` : value) as T;
  if (Array.isArray(value)) return value.map(withApiBase) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, withApiBase(item)])) as T;
  }
  return value;
}
