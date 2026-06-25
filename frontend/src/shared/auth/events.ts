// Global auth events bridge the non-React API client to the React auth state.
// The api client can't call hooks, so on an unrecoverable 401 (refresh failed)
// or a 403 it dispatches a DOM event that AuthProvider listens for.

export const AUTH_UNAUTHORIZED = "auth:unauthorized";
export const AUTH_FORBIDDEN = "auth:forbidden";

export function emitUnauthorized() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED));
  }
}

export function emitForbidden(detail?: string) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(AUTH_FORBIDDEN, { detail }));
  }
}
