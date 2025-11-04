import { Component, ReactNode } from 'react';
import './ErrorBoundary.css';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  message: string;
}

/**
 * Catches render errors and displays a friendly fallback instead of crashing the view.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public override state: ErrorBoundaryState = {
    hasError: false,
    message: 'Something went wrong.',
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    const trimmedMessage = error.message.trim();

    return {
      hasError: true,
      message: trimmedMessage.length > 0 ? trimmedMessage : 'Unexpected application error.',
    };
  }

  public override componentDidCatch(error: Error): void {
    console.error('UI error boundary caught:', error);
  }

  private handleReload = () => {
    this.setState({ hasError: false, message: 'Something went wrong.' });
    window.location.reload();
  };

  public override render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="error-boundary" role="alert">
          <h2>We hit a snag</h2>
          <p>{this.state.message}</p>
          <button onClick={this.handleReload}>Reload App</button>
        </div>
      );
    }

    return this.props.children;
  }
}
