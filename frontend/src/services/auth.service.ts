import type { LoginPayload, RegisterPayload, User } from "@/types/auth";
import { apiClient } from "./api-client";

/**
 * BACKEND INTEGRATION POINT – authentication
 *   POST /auth/login     (LoginPayload)    -> User   (sets httpOnly session cookie)
 *   POST /auth/register  (RegisterPayload) -> User
 *   POST /auth/logout                      -> 204
 *   GET  /auth/me                          -> User   (401 when signed out)
 */
export interface AuthService {
  me(signal?: AbortSignal): Promise<User>;
  login(payload: LoginPayload): Promise<User>;
  register(payload: RegisterPayload): Promise<User>;
  logout(): Promise<void>;
}

const httpAuthService: AuthService = {
  me: (signal) => apiClient.get<User>("/auth/me", { signal }),
  login: (payload) => apiClient.post<User>("/auth/login", payload),
  register: (payload) => apiClient.post<User>("/auth/register", payload),
  logout: () => apiClient.post<void>("/auth/logout"),
};

export const authService: AuthService = httpAuthService;
