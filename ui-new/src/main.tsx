import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {
  createTheme,
  defaultVariantColorsResolver,
  MantineProvider,
  type VariantColorsResolver,
} from '@mantine/core'
import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import '@mantine/core/styles.css'
import './index.css'
import { ApiError } from '@/api/client'
import { App } from '@/App'
import { ErrorBoundary } from '@/components/ErrorBoundary'

const variantColorResolver: VariantColorsResolver = (input) => {
  if (input.variant === 'filled') {
    return {
      background: 'var(--mantine-color-white)',
      hover: 'var(--mantine-color-white)',
      color: 'var(--mantine-color-black)',
      border: 'transparent',
    }
  }
  if (['default', 'light', 'subtle'].includes(input.variant)) {
    return {
      background:
        input.variant === 'subtle' ? 'transparent' : 'var(--mantine-color-black)',
      hover:
        input.variant === 'subtle'
          ? 'rgba(0,0,0,0.5)'
          : 'var(--mantine-color-black)',
      color: 'var(--mantine-color-white)',
      border: 'transparent',
    }
  }
  if (input.variant === 'outline') {
    return {
      background: 'transparent',
      hover: 'var(--mantine-color-white)',
      color: 'var(--mantine-color-white)',
      hoverColor: 'var(--mantine-color-black)',
      border: 'transparent',
    }
  }
  return defaultVariantColorsResolver(input)
}

const theme = createTheme({
  primaryColor: 'gray',
  primaryShade: { light: 6, dark: 4 },
  variantColorResolver,
})

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
})

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
  </StrictMode>,
)
