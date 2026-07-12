"use client";

import React from "react";
import { captureError } from "@hostel/utils";
import { ErrorState } from "./ErrorState";

type Props = {
  children: React.ReactNode;
  /** Custom fallback. Receives the error and a reset callback. */
  fallback?: (error: unknown, reset: () => void) => React.ReactNode;
  /** Label included in the monitoring report to locate the boundary. */
  boundary?: string;
  /** Render the compact (inline) error UI instead of the full-height screen. */
  compact?: boolean;
};

type State = { error: unknown };

/**
 * Component-level React error boundary. Catches render/lifecycle crashes in its
 * subtree, reports them to monitoring, and shows a graceful fallback with a
 * working Retry. Use around risky widgets (charts, dynamic imports, tables fed
 * by untrusted shapes) so one broken component never blanks the whole page.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: unknown): State {
    return { error };
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo) {
    captureError(error, {
      boundary: this.props.boundary ?? "ErrorBoundary",
      componentStack: info.componentStack,
    });
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (error !== null) {
      if (this.props.fallback) return this.props.fallback(error, this.reset);
      return (
        <ErrorState
          error={error}
          onRetry={this.reset}
          compact={this.props.compact}
          description="This section failed to render. You can retry just this part."
        />
      );
    }
    return this.props.children;
  }
}
