/** Types for the Super-Admin discovery-review moderation queue. Mirrors
 * apps.discovery's ReviewModerationSerializer (mounted at /api/platform/discovery/). */

export type FlaggedReview = {
  id: string;
  hostel: string;
  hostel_name: string;
  author: string | null;
  rating: number;
  title: string;
  body: string;
  status: string;
  verification_method: string;
  resident_name_snapshot: string;
  stay_start: string | null;
  stay_end: string | null;
  flag_count: number;
  created_at: string;
};
