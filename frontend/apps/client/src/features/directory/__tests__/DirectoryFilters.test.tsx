import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
let params = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => params,
}));

import { DirectoryFilters } from "../DirectoryFilters";

describe("DirectoryFilters", () => {
  beforeEach(() => {
    push.mockClear();
    params = new URLSearchParams();
  });

  // Select #0 = hostel type, #1 = minimum rating, #2 = ordering (DOM order in
  // the component — none of the <Select>s expose an accessible name here).
  function selects() {
    return screen.getAllByRole("combobox");
  }

  it("pushes the right query string when a hostel type is selected", async () => {
    const user = userEvent.setup();
    render(<DirectoryFilters />);

    await user.selectOptions(selects()[0], "girls");

    expect(push).toHaveBeenCalledTimes(1);
    expect(push).toHaveBeenCalledWith("/hostels?hostel_type=girls");
  });

  it("keeps an already-set filter when a different one changes", async () => {
    params = new URLSearchParams({ hostel_type: "boys" });
    const user = userEvent.setup();
    render(<DirectoryFilters />);

    await user.selectOptions(selects()[1], "4");

    expect(push).toHaveBeenCalledTimes(1);
    const [url] = push.mock.calls[0];
    const query = new URLSearchParams(String(url).split("?")[1]);
    expect(query.get("hostel_type")).toBe("boys");
    expect(query.get("min_rating")).toBe("4");
  });

  it("always strips `page` from the URL on any change", async () => {
    params = new URLSearchParams({ hostel_type: "boys", page: "3" });
    const user = userEvent.setup();
    render(<DirectoryFilters />);

    await user.selectOptions(selects()[2], "name");

    expect(push).toHaveBeenCalledTimes(1);
    const [url] = push.mock.calls[0];
    const query = new URLSearchParams(String(url).split("?")[1]);
    expect(query.has("page")).toBe(false);
    expect(query.get("ordering")).toBe("name");
    expect(query.get("hostel_type")).toBe("boys");
  });

  it("commits a search on Enter and strips page from that update too", async () => {
    params = new URLSearchParams({ page: "2" });
    const user = userEvent.setup();
    render(<DirectoryFilters />);

    const search = screen.getByPlaceholderText("Search by name or city…");
    await user.type(search, "Everest{Enter}");

    expect(push).toHaveBeenCalledWith("/hostels?search=Everest");
  });

  it("commits a search on blur", async () => {
    const user = userEvent.setup();
    render(
      <div>
        <DirectoryFilters />
        <button>elsewhere</button>
      </div>
    );

    const search = screen.getByPlaceholderText("Search by name or city…");
    await user.type(search, "Sunrise");
    await user.click(screen.getByRole("button", { name: "elsewhere" }));

    expect(push).toHaveBeenCalledWith("/hostels?search=Sunrise");
  });

  it("removes a filter (deletes the key) when reset to the empty option", async () => {
    params = new URLSearchParams({ hostel_type: "boys" });
    const user = userEvent.setup();
    render(<DirectoryFilters />);

    await user.selectOptions(selects()[0], "");

    expect(push).toHaveBeenCalledWith("/hostels");
  });
});
