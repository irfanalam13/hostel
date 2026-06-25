"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

export type ToastVariant = "success" | "error" | "warning" | "info";

export type Toast = {
  id: string;
  variant: ToastVariant;
  title?: string;
  message: string;
  duration: number; // ms; 0 = sticky
};

type ToastInput = Omit<Partial<Toast>, "id"> & { message: string };

type ToastContextValue = {
  show: (input: ToastInput) => string;
  success: (message: string, title?: string) => string;
  error: (message: string, title?: string) => string;
  warning: (message: string, title?: string) => string;
  info: (message: string, title?: string) => string;
  dismiss: (id: string) => void;
  clear: () => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const DEFAULT_DURATION = 4500;
let counter = 0;
function nextId() {
  counter += 1;
  return `toast_${Date.now()}_${counter}`;
}

const VARIANT_STYLES: Record<ToastVariant, { bar: string; icon: string; ring: string }> = {
  success: { bar: "bg-emerald-500", icon: "✓", ring: "ring-emerald-100" },
  error: { bar: "bg-red-500", icon: "✕", ring: "ring-red-100" },
  warning: { bar: "bg-amber-500", icon: "!", ring: "ring-amber-100" },
  info: { bar: "bg-blue-500", icon: "i", ring: "ring-blue-100" },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    setToasts((list) => list.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const show = useCallback(
    (input: ToastInput) => {
      const id = nextId();
      const toast: Toast = {
        id,
        variant: input.variant ?? "info",
        title: input.title,
        message: input.message,
        duration: input.duration ?? DEFAULT_DURATION,
      };
      setToasts((list) => {
        // De-dupe identical back-to-back messages (e.g. a retry loop firing the
        // same API error) so the user isn't spammed.
        const last = list[list.length - 1];
        if (last && last.message === toast.message && last.variant === toast.variant) {
          return list;
        }
        return [...list, toast];
      });
      if (toast.duration > 0) {
        const timer = setTimeout(() => dismiss(id), toast.duration);
        timers.current.set(id, timer);
      }
      return id;
    },
    [dismiss]
  );

  const clear = useCallback(() => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current.clear();
    setToasts([]);
  }, []);

  // Clean up any pending timers on unmount.
  useEffect(() => {
    const map = timers.current;
    return () => {
      map.forEach((t) => clearTimeout(t));
      map.clear();
    };
  }, []);

  const value = useMemo<ToastContextValue>(
    () => ({
      show,
      dismiss,
      clear,
      success: (message, title) => show({ message, title, variant: "success" }),
      error: (message, title) => show({ message, title, variant: "error", duration: 7000 }),
      warning: (message, title) => show({ message, title, variant: "warning" }),
      info: (message, title) => show({ message, title, variant: "info" }),
    }),
    [show, dismiss, clear]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toaster toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

function Toaster({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex flex-col items-center gap-2 px-3 sm:items-end sm:pr-4"
    >
      {toasts.map((t) => {
        const style = VARIANT_STYLES[t.variant];
        return (
          <div
            key={t.id}
            role={t.variant === "error" ? "alert" : "status"}
            className={`pointer-events-auto flex w-full max-w-sm items-start gap-3 overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-lg ring-1 ${style.ring}`}
          >
            <div className={`flex h-full w-1.5 shrink-0 ${style.bar}`} aria-hidden />
            <div className="flex flex-1 items-start gap-2 py-3 pr-1">
              <span
                className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full text-[11px] font-bold text-white ${style.bar}`}
                aria-hidden
              >
                {style.icon}
              </span>
              <div className="min-w-0 flex-1">
                {t.title ? (
                  <div className="text-sm font-semibold text-zinc-900">{t.title}</div>
                ) : null}
                <div className="break-words text-sm text-zinc-700">{t.message}</div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onDismiss(t.id)}
              aria-label="Dismiss notification"
              className="px-3 py-3 text-zinc-400 transition hover:text-zinc-700"
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a <ToastProvider>.");
  }
  return ctx;
}
