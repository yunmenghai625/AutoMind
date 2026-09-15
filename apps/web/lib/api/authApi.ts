import { http } from "@/lib/api/apiClient";
import { authHeaders } from "@/lib/api/identity";

export interface CurrentUser {
  kind: "guest" | "registered";
  user_id: string | null;
  email: string | null;
  role: string;
}

export interface AdminSession {
  accessToken: string;
  tokenType: "Bearer";
  expiresAt: string;
  user: CurrentUser;
}

export function loginAdmin(
  username: string,
  password: string,
): Promise<AdminSession> {
  return http<AdminSession>("/api/v1/auth/admin/login", {
    method: "POST",
    body: { username, password },
  });
}

export function getCurrentUser(): Promise<CurrentUser> {
  return http<CurrentUser>("/api/v1/auth/me", { headers: authHeaders() });
}
