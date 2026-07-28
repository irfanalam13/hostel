import { StarRating } from "@hostel/ui";
import { getReviewsSectionData } from "./api";
import { ReviewList } from "./ReviewList";
import { WriteReviewCTA } from "./WriteReviewCTA";

/**
 * Reviews are platform-mandated content, not part of the owner's
 * website-builder `sections` model — rendered unconditionally after the
 * owner-ordered sections, not through `renderSection`.
 */
export async function ReviewsSection({ hostelSlug }: { hostelSlug: string }) {
  const { rating, reviews, next } = await getReviewsSectionData(hostelSlug);

  return (
    <section id="reviews" className="scroll-mt-20 border-t border-black/5 py-14">
      <div className="mx-auto max-w-5xl px-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-[var(--site-secondary)]">Reviews</h2>
            <div className="mt-2 flex items-center gap-2">
              <StarRating value={rating.average} color="var(--site-accent)" />
              <span className="font-medium text-gray-900">{rating.average.toFixed(1)}</span>
              <span className="text-sm text-gray-500">
                ({rating.count} {rating.count === 1 ? "review" : "reviews"})
              </span>
            </div>
          </div>
          <WriteReviewCTA hostelSlug={hostelSlug} />
        </div>

        <div className="mt-8">
          <ReviewList initial={reviews} initialNext={next} />
        </div>
      </div>
    </section>
  );
}
