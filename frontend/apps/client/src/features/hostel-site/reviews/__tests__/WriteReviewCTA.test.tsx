import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { EligibilityState } from "../useReviewEligibility";
import type { MyReview } from "../reviewsApi";

const reload = vi.fn();
let state: EligibilityState = { status: "checking" };

vi.mock("../useReviewEligibility", () => ({
  useReviewEligibility: () => ({ state, reload }),
}));

vi.mock("../ConsumerAuthForm", () => ({
  ConsumerAuthForm: () => <div data-testid="consumer-auth-form-stub">stub auth form</div>,
}));

vi.mock("../ReviewForm", () => ({
  ReviewForm: () => <div data-testid="review-form-stub">stub review form</div>,
}));

const deleteReview = vi.fn();
vi.mock("../reviewsApi", () => ({
  deleteReview: (...args: unknown[]) => deleteReview(...args),
}));

import { WriteReviewCTA } from "../WriteReviewCTA";

const USER = { id: 1, username: "consumer1", email: "c@example.com" };

const PUBLISHED_REVIEW: MyReview = {
  id: "rev-1",
  rating: 4,
  title: "Really nice",
  body: "Would stay again.",
  author_display_name: "Me",
  verification_method: "verified_resident",
  stay_start: null,
  stay_end: null,
  owner_response: null,
  created_at: "2026-01-01T00:00:00Z",
  status: "published",
};

const PENDING_REVIEW: MyReview = { ...PUBLISHED_REVIEW, status: "pending" };

describe("WriteReviewCTA", () => {
  beforeEach(() => {
    reload.mockReset();
    deleteReview.mockReset();
  });

  it("checking: shows the status spinner", () => {
    state = { status: "checking" };
    render(<WriteReviewCTA hostelSlug="everest-hostel" />);
    expect(screen.getByText("Checking your review status…")).toBeInTheDocument();
  });

  it("anonymous: renders a usable 'Write a review' affordance, which reveals the auth form", async () => {
    state = { status: "anonymous" };
    const user = userEvent.setup();
    render(<WriteReviewCTA hostelSlug="everest-hostel" />);

    const button = screen.getByRole("button", { name: "Write a review" });
    expect(button).toBeInTheDocument();
    expect(button).toBeEnabled();

    await user.click(button);
    expect(screen.getByTestId("consumer-auth-form-stub")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Write a review" })).not.toBeInTheDocument();
  });

  it("no_review: renders a usable 'Write a review' affordance, which reveals the review form", async () => {
    state = { status: "no_review", user: USER };
    const user = userEvent.setup();
    render(<WriteReviewCTA hostelSlug="everest-hostel" />);

    const button = screen.getByRole("button", { name: "Write a review" });
    expect(button).toBeInTheDocument();

    await user.click(button);
    expect(screen.getByTestId("review-form-stub")).toBeInTheDocument();
  });

  it("has_review + status=pending: shows the pending notice AND the existing review AND edit/delete controls", () => {
    state = { status: "has_review", user: USER, review: PENDING_REVIEW };
    render(<WriteReviewCTA hostelSlug="everest-hostel" />);

    // Notice banner — never silently hidden.
    expect(screen.getByText("Submitted — pending confirmation")).toBeInTheDocument();
    expect(
      screen.getByText(
        "We couldn't automatically confirm your stay. The hostel will review and publish it shortly."
      )
    ).toBeInTheDocument();

    // The review itself is still fully shown.
    expect(screen.getByText("Really nice")).toBeInTheDocument();
    expect(screen.getByText("Would stay again.")).toBeInTheDocument();

    // Controls are still available, not hidden because of the pending status.
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("has_review + status=published: shows no notice banner", () => {
    state = { status: "has_review", user: USER, review: PUBLISHED_REVIEW };
    render(<WriteReviewCTA hostelSlug="everest-hostel" />);

    expect(screen.getByText("Really nice")).toBeInTheDocument();
    expect(screen.queryByText("Submitted — pending confirmation")).not.toBeInTheDocument();
    expect(screen.queryByText("Not published")).not.toBeInTheDocument();
    expect(screen.queryByText("Under review")).not.toBeInTheDocument();
    expect(screen.queryByText("Removed")).not.toBeInTheDocument();
    // Still has edit/delete either way.
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("has_review: clicking Edit swaps in the review form stub, pre-populated for editing", async () => {
    state = { status: "has_review", user: USER, review: PUBLISHED_REVIEW };
    const user = userEvent.setup();
    render(<WriteReviewCTA hostelSlug="everest-hostel" />);

    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByTestId("review-form-stub")).toBeInTheDocument();
  });

  it("has_review: clicking Delete asks for confirmation and calls deleteReview + reload when confirmed", async () => {
    state = { status: "has_review", user: USER, review: PUBLISHED_REVIEW };
    vi.spyOn(window, "confirm").mockReturnValue(true);
    deleteReview.mockResolvedValue(undefined);
    reload.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<WriteReviewCTA hostelSlug="everest-hostel" />);

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(window.confirm).toHaveBeenCalled();
    expect(deleteReview).toHaveBeenCalledWith("rev-1");
    expect(reload).toHaveBeenCalled();
  });

  it("has_review: clicking Delete does nothing when the confirmation is declined", async () => {
    state = { status: "has_review", user: USER, review: PUBLISHED_REVIEW };
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(<WriteReviewCTA hostelSlug="everest-hostel" />);

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(deleteReview).not.toHaveBeenCalled();
  });
});
