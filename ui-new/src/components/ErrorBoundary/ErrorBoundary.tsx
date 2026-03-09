/* eslint-disable no-restricted-syntax */
import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'grid',
            placeItems: 'center',
            padding: '1rem',
            background: '#0b0d10',
            color: '#f8fafc',
          }}
        >
          <div
            style={{
              width: 'min(100%, 36rem)',
              padding: '1.25rem',
              borderRadius: '1rem',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              background: 'rgba(18, 22, 28, 0.96)',
              boxShadow: '0 18px 36px rgba(0, 0, 0, 0.24)',
            }}
          >
            <p
              style={{
                margin: 0,
                color: '#9be341',
                fontSize: '0.78rem',
                fontWeight: 700,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
              }}
            >
              UI error
            </p>
            <h1 style={{ margin: '0.65rem 0 0', fontSize: '1.5rem', lineHeight: 1.1 }}>
              This screen ran into a problem
            </h1>
            <p style={{ margin: '0.9rem 0 0', color: '#aeb9c8', lineHeight: 1.5 }}>
              {import.meta.env.DEV
                ? (this.state.error?.message ?? 'An unexpected error occurred')
                : 'Refresh the page or go back to a stable screen and try again.'}
            </p>
            <button
              type="button"
              onClick={this.handleReset}
              style={{
                marginTop: '1rem',
                minHeight: '2.75rem',
                padding: '0.7rem 1rem',
                borderRadius: '0.9rem',
                border: '1px solid rgba(255, 255, 255, 0.14)',
                background: 'linear-gradient(180deg, #181b1f, #0f1215)',
                color: '#f8fafc',
                cursor: 'pointer',
              }}
            >
              Try again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
