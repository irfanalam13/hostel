"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";
import { Button } from "./Button";

type ConfirmOptions = {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  /** Style the confirm button as destructive (red). */
  danger?: boolean;
};

type ConfirmContextValue = {
  /** Resolves true if confirmed, false if cancelled/dismissed. */
  confirm: (options: ConfirmOptions) => Promise<boolean>;
};

const ConfirmContext = createContext<ConfirmContextValue | null>(null);

type DialogState = ConfirmOptions & { open: boolean };

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<DialogState>({ open: false, message: "" });
  const resolver = useRef<((value: boolean) => void) | null>(null);

  const settle = useCallback((value: boolean) => {
    setState((s) => ({ ...s, open: false }));
    resolver.current?.(value);
    resolver.current = null;
  }, []);

  const confirm = useCallback((options: ConfirmOptions) => {
    setState({ open: true, ...options });
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
    });
  }, []);

  const value = useMemo<ConfirmContextValue>(() => ({ confirm }), [confirm]);

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      {state.open ? (
        <div
          className="fixed inset-0 z-[90] grid place-items-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => settle(false)}
        >
          <div
            className="w-full max-w-sm rounded-2xl border border-zinc-200 bg-white p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-base font-semibold text-zinc-900">
              {state.title ?? "Are you sure?"}
            </div>
            <p className="mt-2 text-sm text-zinc-600">{state.message}</p>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => settle(false)}>
                {state.cancelText ?? "Cancel"}
              </Button>
              <Button
                variant={state.danger ? "danger" : "primary"}
                onClick={() => settle(true)}
                autoFocus
              >
                {state.confirmText ?? "Confirm"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </ConfirmContext.Provider>
  );
}

export function useConfirm(): ConfirmContextValue["confirm"] {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within a <ConfirmProvider>.");
  return ctx.confirm;
}
