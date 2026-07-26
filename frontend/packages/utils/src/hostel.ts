type HostelContext = {
  code?: string; // preferred
  id?: string;   // fallback
};

const KEY = "hostel_context_v1";

function safeParse(json: string | null): HostelContext {
  try {
    return json ? (JSON.parse(json) as HostelContext) : {};
  } catch {
    return {};
  }
}

export const hostelStore = {
  get(): HostelContext {
    if (typeof window === "undefined") return {};
    return safeParse(localStorage.getItem(KEY));
  },

  set(ctx: HostelContext) {
    if (typeof window === "undefined") return;
    localStorage.setItem(KEY, JSON.stringify(ctx));
  },

  clear() {
    if (typeof window === "undefined") return;
    localStorage.removeItem(KEY);
  },

  getCode(): string | undefined {
    return this.get().code?.trim() || undefined;
  },

  getId(): string | undefined {
    return this.get().id?.trim() || undefined;
  },
};