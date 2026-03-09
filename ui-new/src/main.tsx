import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import {
  createTheme,
  defaultVariantColorsResolver,
  Input,
  InputWrapper,
  MantineProvider,
  Menu,
  Tabs,
  Tooltip,
  type VariantColorsResolver,
} from '@mantine/core';
import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import './index.css';
import { ApiError } from '@/api/client';
import { App } from '@/App';
import { ErrorBoundary } from '@/components/ErrorBoundary';

const variantColorResolver: VariantColorsResolver = (input) => {
  if (input.variant === 'filled') {
    return {
      background: 'var(--app-accent)',
      hover: 'var(--app-accent-strong)',
      color: '#07110a',
      border: 'transparent',
    };
  }
  if (['default', 'light', 'subtle'].includes(input.variant)) {
    return {
      background:
        input.variant === 'subtle' ? 'transparent' : 'linear-gradient(180deg, #181b1f, #0f1215)',
      hover: input.variant === 'subtle' ? 'rgba(255,255,255,0.05)' : '#1d2126',
      color: 'var(--app-text-primary)',
      border: input.variant === 'subtle' ? 'transparent' : '1px solid var(--app-border-subtle)',
    };
  }
  if (input.variant === 'outline') {
    return {
      background: 'transparent',
      hover: 'rgba(255,255,255,0.04)',
      color: 'var(--app-text-primary)',
      hoverColor: 'var(--app-text-primary)',
      border: '1px solid var(--app-border-strong)',
    };
  }
  return defaultVariantColorsResolver(input);
};

const theme = createTheme({
  primaryColor: 'brand',
  primaryShade: { light: 5, dark: 5 },
  defaultRadius: 'xl',
  fontFamily: 'var(--app-font-sans)',
  headings: {
    fontFamily: 'var(--app-font-display)',
  },
  black: '#0d1116',
  white: '#f8fafc',
  colors: {
    brand: [
      '#f3ffe5',
      '#e5ffbe',
      '#d5fb95',
      '#c4f66c',
      '#afe84c',
      '#9be341',
      '#7cc01d',
      '#5b9113',
      '#3a600b',
      '#1b3103',
    ],
  },
  variantColorResolver,
  components: {
    Tooltip: Tooltip.extend({
      defaultProps: {
        withArrow: true,
      },
      styles: {
        tooltip: {
          background: 'rgba(10, 13, 17, 0.98)',
          color: 'var(--app-text-primary)',
          border: '1px solid rgba(155, 227, 65, 0.2)',
          boxShadow: 'var(--app-shadow-soft)',
          backdropFilter: 'blur(12px)',
          borderRadius: '0.9rem',
          padding: '0.55rem 0.75rem',
        },
        arrow: {
          background: 'rgba(10, 13, 17, 0.98)',
          border: '1px solid rgba(155, 227, 65, 0.2)',
        },
      },
    }),
    InputWrapper: InputWrapper.extend({
      styles: {
        label: {
          color: 'var(--app-text-secondary)',
          fontSize: '0.82rem',
          fontWeight: 700,
          letterSpacing: '0.02em',
          marginBottom: '0.35rem',
        },
        description: {
          color: 'var(--app-text-muted)',
        },
      },
    }),
    Input: Input.extend({
      styles: {
        input: {
          background: 'var(--app-control-surface)',
          border: '1px solid var(--app-control-border)',
          color: 'var(--app-text-primary)',
          borderRadius: '0.9rem',
          minHeight: '2.8rem',
          boxShadow: 'var(--app-control-shadow)',
        },
        section: {
          color: 'var(--app-text-muted)',
        },
      },
    }),
    Tabs: Tabs.extend({
      styles: {
        tab: {
          outlineOffset: 2,
        },
      },
    }),
    Menu: Menu.extend({
      styles: {
        dropdown: {
          background: 'rgba(10, 13, 17, 0.98)',
          border: '1px solid var(--app-border-subtle)',
          boxShadow: 'var(--app-shadow-soft)',
          backdropFilter: 'blur(12px)',
        },
        item: {
          borderRadius: '0.8rem',
        },
      },
    }),
  },
});

// Global error handler for TanStack Query
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      console.error('Query error:', error);
      // Log to error tracking service in production
      // import.meta.env is Vite's way of accessing env variables
      if (import.meta.env.PROD) {
        // Example: Sentry.captureException(error);
      }
    },
  }),
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <MantineProvider theme={theme} defaultColorScheme="dark">
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </MantineProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>
);
