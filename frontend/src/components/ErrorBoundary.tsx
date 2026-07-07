"use client";

import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  /** Optional label for console diagnostics. */
  label?: string;
}

interface State {
  hasError: boolean;
}

/**
 * Generic client error boundary. Any render/runtime error in `children`
 * (e.g. a WebGL context failure inside react-three-fiber) is caught and the
 * `fallback` is shown instead of crashing the entire page tree.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    // Surface it for debugging without taking the page down.
    console.error(`[ErrorBoundary${this.props.label ? `:${this.props.label}` : ''}]`, error);
  }

  render() {
    if (this.state.hasError) return this.props.fallback ?? null;
    return this.props.children;
  }
}
