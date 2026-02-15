import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {
  createTheme,
  defaultVariantColorsResolver,
  MantineProvider,
  type VariantColorsResolver,
} from '@mantine/core'

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
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import '@mantine/core/styles.css'
import './index.css'
import { App } from '@/App'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme} defaultColorScheme="dark">
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </MantineProvider>
    </QueryClientProvider>
  </StrictMode>,
)
