import { Component, type ErrorInfo, type ReactNode } from "react";

import { ErrorMessage } from "@/components/ErrorMessage";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class GlobalErrorBoundary extends Component<Props, State> {
  state: State = {
    hasError: false,
    message: "",
  };

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      message: error.message || "An unexpected UI error occurred",
    };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Keep console logging for developers; never send secrets
    console.error("UI error boundary caught", error.name, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="app-main">
          <ErrorMessage
            title="Something went wrong"
            message={this.state.message}
            onRetry={() => window.location.assign("/")}
          />
        </div>
      );
    }
    return this.props.children;
  }
}
