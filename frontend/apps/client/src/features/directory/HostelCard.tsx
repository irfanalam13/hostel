import { StarRating } from "@hostel/ui";
import type { DirectoryHostel } from "./api";

const AMENITY_LABELS: Record<string, string> = {
  wifi: "WiFi", cctv: "CCTV", laundry: "Laundry", hot_water: "Hot water",
  attached_bathroom: "Attached bathroom", food_included: "Food included",
  parking: "Parking", study_room: "Study room", gym: "Gym", ac: "AC",
};

/* eslint-disable @next/next/no-img-element -- owner-uploaded remote assets */
export function HostelCard({ hostel }: { hostel: DirectoryHostel }) {
  return (
    <a
      href={hostel.public_url || "#"}
      className="group block overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)] transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="aspect-[4/3] w-full bg-[var(--background-secondary)]">
        {hostel.cover_image ? (
          <img
            src={hostel.cover_image}
            alt=""
            className="h-full w-full object-cover transition group-hover:scale-[1.02]"
          />
        ) : (
          <div className="grid h-full w-full place-items-center text-4xl">🏨</div>
        )}
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="line-clamp-1 font-semibold text-[var(--foreground)]">{hostel.name}</h3>
          {hostel.hostel_type ? (
            <span className="shrink-0 rounded-full bg-[var(--accent-soft)] px-2 py-0.5 text-xs font-medium text-[var(--accent)]">
              {hostel.hostel_type}
            </span>
          ) : null}
        </div>
        {(hostel.city || hostel.district) && (
          <p className="mt-0.5 text-sm text-[var(--foreground-secondary)]">
            {[hostel.city, hostel.district].filter(Boolean).join(", ")}
          </p>
        )}
        <div className="mt-2 flex items-center gap-1.5">
          <StarRating value={hostel.average_rating} size="sm" />
          <span className="text-sm font-medium text-[var(--foreground)]">
            {hostel.average_rating.toFixed(1)}
          </span>
          <span className="text-sm text-[var(--foreground-secondary)]">
            ({hostel.rating_count} {hostel.rating_count === 1 ? "review" : "reviews"})
          </span>
        </div>
        {hostel.amenity_tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {hostel.amenity_tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-[var(--border)] px-2 py-0.5 text-xs text-[var(--foreground-secondary)]"
              >
                {AMENITY_LABELS[tag] || tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </a>
  );
}
