"use client";

/**
 * Client-side mutations for the review-writing flow on a hostel's public
 * site: consumer signup/login, review CRUD, flagging. Built on
 * `discoveryFetch` (features/discovery/discoveryFetch.ts) — deliberately not
 * `@hostel/api`'s `apiFetch`, since that always attaches an `X-Workspace`
 * header derived from the current hostname, which would make the backend
 * reject a consumer session (bound to the hidden platform workspace) with
 * "This session belongs to a different workspace" whenever this UI renders
 * on a tenant's own subdomain.
 */
import { discoveryFetch } from "@/features/discovery/discoveryFetch";
import type { HostelReview } from "./api";

export type ConsumerUser = {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role?: string;
};

export async function requestSignupOtp(email: string): Promise<void> {
  await discoveryFetch("/auth/signup/request-otp/", { method: "POST", body: { email } });
}

export async function consumerSignup(input: {
  full_name: string;
  phone: string;
  email: string;
  otp: string;
  password: string;
  password2: string;
}): Promise<{ user: ConsumerUser }> {
  return discoveryFetch("/auth/consumer/signup/", { method: "POST", body: input });
}

export async function consumerLogin(input: { email: string; password: string }): Promise<{ user: ConsumerUser }> {
  return discoveryFetch("/auth/consumer/login/", { method: "POST", body: input });
}

export async function getCurrentConsumer(): Promise<ConsumerUser | null> {
  try {
    return await discoveryFetch<ConsumerUser>("/auth/me/", { retryOn401: false });
  } catch {
    return null;
  }
}

export type MyReview = HostelReview & { status: "pending" | "published" | "rejected" | "flagged" | "removed" };

export async function getMyReview(hostelSlug: string): Promise<MyReview | null> {
  try {
    return await discoveryFetch<MyReview>(`/discovery/reviews/mine/?hostel=${encodeURIComponent(hostelSlug)}`);
  } catch {
    return null;
  }
}

export async function submitReview(input: { hostel: string; rating: number; title: string; body: string }) {
  return discoveryFetch("/discovery/reviews/", { method: "POST", body: input });
}

export async function updateReview(id: string, input: { rating: number; title: string; body: string }) {
  return discoveryFetch(`/discovery/reviews/${id}/`, { method: "PATCH", body: input });
}

export async function deleteReview(id: string) {
  return discoveryFetch(`/discovery/reviews/${id}/`, { method: "DELETE" });
}

export async function flagReview(id: string, reason: string, note?: string) {
  return discoveryFetch(`/discovery/reviews/${id}/flag/`, { method: "POST", body: { reason, note } });
}
