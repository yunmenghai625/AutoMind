const ACCESS_TOKEN_KEY = "automind-access-token";
const GUEST_ID_KEY = "automind-guest-id";
export const AUTH_CHANGE_EVENT = "automind-auth-change";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function hasAccessToken(): boolean {
  return Boolean(getAccessToken());
}

export function setAccessToken(token: string): void {
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
    window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
  }
}

export function clearAccessToken(): void {
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
  }
}

export function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = getAccessToken();
  if (token) return { Authorization: `Bearer ${token}` };

  let guestId = window.localStorage.getItem(GUEST_ID_KEY);
  if (!guestId) {
    guestId = window.crypto.randomUUID();
    window.localStorage.setItem(GUEST_ID_KEY, guestId);
  }
  return { "X-Guest-ID": guestId };
}
