import { apiFetch } from "@hostel/api";
import type { FlaggedReview } from "../types/moderation.types";

function m<T>(path: string, options: RequestInit = {}) {
  return apiFetch<T>(`/platform/discovery${path}`, options);
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const moderationApi = {
  flagged: () => m<FlaggedReview[]>("/flagged/"),
  unflag: (id: string) => m<FlaggedReview>(`/reviews/${id}/unflag/`, { method: "POST", ...json({}) }),
  remove: (id: string) => m<FlaggedReview>(`/reviews/${id}/remove/`, { method: "POST", ...json({}) }),
};
