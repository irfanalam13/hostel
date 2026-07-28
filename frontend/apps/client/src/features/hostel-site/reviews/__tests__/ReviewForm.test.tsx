import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const submitReview = vi.fn();
const updateReview = vi.fn();

vi.mock("../reviewsApi", () => ({
  submitReview: (...args: unknown[]) => submitReview(...args),
  updateReview: (...args: unknown[]) => updateReview(...args),
}));

import { ReviewForm } from "../ReviewForm";
import type { MyReview } from "../reviewsApi";

const EXISTING: MyReview = {
  id: "rev-1",
  rating: 4,
  title: "Solid stay",
  body: "Clean rooms and friendly staff.",
  author_display_name: "J. Doe",
  verification_method: "verified_resident",
  stay_start: null,
  stay_end: null,
  owner_response: null,
  created_at: "2026-01-01T00:00:00Z",
  status: "published",
};

describe("ReviewForm", () => {
  beforeEach(() => {
    submitReview.mockReset();
    updateReview.mockReset();
    submitReview.mockResolvedValue({});
    updateReview.mockResolvedValue({});
  });

  it("shows a validation message and does not submit when rating is 0", async () => {
    const onSaved = vi.fn();
    const user = userEvent.setup();
    render(<ReviewForm hostelSlug="everest-hostel" onSaved={onSaved} />);

    await user.type(screen.getByPlaceholderText("Give your review a title"), "Title");
    await user.type(
      screen.getByPlaceholderText("Share your experience living here…"),
      "Body text"
    );
    await user.click(screen.getByRole("button", { name: "Submit review" }));

    expect(await screen.findByText("Choose a star rating.")).toBeInTheDocument();
    expect(submitReview).not.toHaveBeenCalled();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("submits with the right args and calls onSaved when creating a new review", async () => {
    const onSaved = vi.fn();
    const user = userEvent.setup();
    render(<ReviewForm hostelSlug="everest-hostel" onSaved={onSaved} />);

    await user.click(screen.getByRole("radio", { name: "5 stars" }));
    await user.type(screen.getByPlaceholderText("Give your review a title"), "Great place");
    await user.type(
      screen.getByPlaceholderText("Share your experience living here…"),
      "Loved every minute."
    );
    await user.click(screen.getByRole("button", { name: "Submit review" }));

    await screen.findByRole("button", { name: "Submit review" }); // still mounted, busy resolved
    expect(submitReview).toHaveBeenCalledTimes(1);
    expect(submitReview).toHaveBeenCalledWith({
      hostel: "everest-hostel",
      rating: 5,
      title: "Great place",
      body: "Loved every minute.",
    });
    expect(updateReview).not.toHaveBeenCalled();
    expect(onSaved).toHaveBeenCalledTimes(1);
  });

  it("pre-fills fields from `existing` and calls updateReview instead on submit", async () => {
    const onSaved = vi.fn();
    const user = userEvent.setup();
    render(<ReviewForm hostelSlug="everest-hostel" existing={EXISTING} onSaved={onSaved} />);

    expect(screen.getByDisplayValue("Solid stay")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Clean rooms and friendly staff.")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "4 stars" })).toHaveAttribute("aria-checked", "true");

    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(updateReview).toHaveBeenCalledTimes(1);
    expect(updateReview).toHaveBeenCalledWith("rev-1", {
      rating: 4,
      title: "Solid stay",
      body: "Clean rooms and friendly staff.",
    });
    expect(submitReview).not.toHaveBeenCalled();
    expect(onSaved).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when Cancel is clicked", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<ReviewForm hostelSlug="everest-hostel" onSaved={vi.fn()} onCancel={onCancel} />);

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
