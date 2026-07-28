import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StarRating } from "../StarRating";

describe("StarRating", () => {
  describe("display mode (no onChange)", () => {
    it("renders role=img with a default aria-label describing the rating", () => {
      render(<StarRating value={3.5} />);
      const el = screen.getByRole("img");
      expect(el).toHaveAttribute("aria-label", "Rated 3.5 out of 5");
    });

    it("respects a custom max in the default aria-label", () => {
      render(<StarRating value={2} max={10} />);
      expect(screen.getByRole("img")).toHaveAttribute("aria-label", "Rated 2.0 out of 10");
    });

    it("prefers an explicit aria-label over the generated one", () => {
      render(<StarRating value={4} aria-label="Average rating" />);
      expect(screen.getByRole("img")).toHaveAttribute("aria-label", "Average rating");
    });

    it("does not render any radio buttons", () => {
      render(<StarRating value={3} />);
      expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
      expect(screen.queryAllByRole("radio")).toHaveLength(0);
    });
  });

  describe("interactive mode (onChange passed)", () => {
    it("renders a radiogroup with `max` radio buttons", () => {
      render(<StarRating value={2} onChange={vi.fn()} />);
      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
      expect(screen.getAllByRole("radio")).toHaveLength(5);
    });

    it("labels each radio with its star count", () => {
      render(<StarRating value={0} onChange={vi.fn()} />);
      expect(screen.getByRole("radio", { name: "1 star" })).toBeInTheDocument();
      expect(screen.getByRole("radio", { name: "2 stars" })).toBeInTheDocument();
      expect(screen.getByRole("radio", { name: "5 stars" })).toBeInTheDocument();
    });

    it("reflects the current value via aria-checked", () => {
      render(<StarRating value={3} onChange={vi.fn()} />);
      const radios = screen.getAllByRole("radio");
      expect(radios[0]).toHaveAttribute("aria-checked", "false");
      expect(radios[1]).toHaveAttribute("aria-checked", "false");
      expect(radios[2]).toHaveAttribute("aria-checked", "true");
      expect(radios[3]).toHaveAttribute("aria-checked", "false");
      expect(radios[4]).toHaveAttribute("aria-checked", "false");
    });

    it("calls onChange(4) when the 4th star is clicked", async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<StarRating value={1} onChange={onChange} />);
      await user.click(screen.getByRole("radio", { name: "4 stars" }));
      expect(onChange).toHaveBeenCalledTimes(1);
      expect(onChange).toHaveBeenCalledWith(4);
    });

    it("respects a custom max for the number of radios rendered", () => {
      render(<StarRating value={0} max={3} onChange={vi.fn()} />);
      expect(screen.getAllByRole("radio")).toHaveLength(3);
    });
  });
});
