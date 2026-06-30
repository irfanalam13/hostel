import { apiFetch } from "@/shared/api/apiClient";

export type SignupPayload = {
  username: string;
  email: string;
  /** 6-digit code emailed by requestSignupOtp() — required to create the account. */
  otp: string;
  password: string;
  password2: string;
  hostel_name: string;
  hostel_phone?: string;
  hostel_address?: string;
  owner_name?: string;
};

export type AuthUser = {
  id: number;
  username: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  is_staff?: boolean;
  is_active?: boolean;
};

export type SignupResponse = {
  user: AuthUser;
  hostel_code?: string | null;
  access: string;
  refresh: string;
};

export const authApi = {
  /** Step 1: email a 6-digit verification code to the given address. */
  requestSignupOtp(payload: { email: string }) {
    return apiFetch<{ detail: string }>("/auth/signup/request-otp/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
    });
  },

  /** Step 2: create the account, supplying the verified OTP. */
  signup(payload: SignupPayload) {
    return apiFetch<SignupResponse>("/auth/signup/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
    });
  },

  me() {
    return apiFetch<AuthUser>("/auth/me/");
  },

  forgotPassword(payload: { email?: string; username?: string }) {
    return apiFetch<{ detail: string }>("/auth/password/forgot/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
    });
  },

  resetPassword(payload: { email_or_username: string; otp: string; new_password: string }) {
    return apiFetch<{ detail: string }>("/auth/password/reset/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
    });
  },

  forgotHostelID(payload: { email_or_username: string }) {
    return apiFetch<{ detail: string }>("/auth/hostel-id/forgot/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
    });
  },
};
