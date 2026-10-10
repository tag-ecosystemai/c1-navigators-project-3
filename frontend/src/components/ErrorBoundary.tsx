import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-surface-primary flex flex-col items-center justify-center p-4">
          <div className="max-w-md w-full bg-surface-secondary rounded-lg border border-border-primary p-6 shadow-xl">
            <h1 className="text-xl font-bold text-rose-500 mb-4">Something went wrong</h1>
            <p className="text-content-secondary mb-4 text-sm">
              {this.state.error?.message || 'An unexpected error occurred in the application.'}
            </p>
            <button
              onClick={this.handleReload}
              className="w-full py-2 px-4 bg-brand-primary hover:bg-brand-secondary text-white rounded-md transition-colors font-medium"
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
